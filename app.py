#!/usr/bin/env python3
"""
RepoCoder API — FastAPI server that:
 1) Loads a local code LLM (default: deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct)
 2) Indexes a codebase folder into a FAISS vector store (code-aware chunking)
 3) Serves an HTTP API to answer repo questions and propose patch diffs

Now with an optional Cursor-style multi‑agent pipeline (planner → coder → judge)
exposed via /query_plus.

Requirements (Python 3.10+ recommended):
  pip install fastapi uvicorn[standard] pydantic transformers accelerate torch
  pip install sentence-transformers faiss-cpu tiktoken rich

GPU setup:
  - PyTorch with CUDA (pip or conda) and a 40 GB VRAM GPU.
  - Optional: set HF_HUB_DISABLE_TELEMETRY=1 and TRANSFORMERS_OFFLINE=1 if fully offline.

Run:
  export MODEL_NAME="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
  export EMBED_MODEL="jinaai/jina-embeddings-v2-base-code"
  python app.py --repo /path/to/your/repo --host 0.0.0.0 --port 8000

Example usage:
  curl -X POST 'http://localhost:8000/query' \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Add input validation to /api/upload and write unit tests.", "top_k": 12}'

For the multi‑agent endpoint:
  curl -X POST 'http://localhost:8000/query_plus' \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Refactor X with tests", "top_k": 24, "temperature": 0.0}'
"""

import os
import sys
import json
import time
from typing import List, Dict, Optional, Any, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console

console = Console()

# Import our modular components
from config import parse_args, get_environment_defaults
from models import IndexRequest, QueryRequest, QueryResponse, ApplyRequest
from indexer import RepoIndexer
from persistent_indexer import PersistentRepoIndexer
from llm import LocalCoder
from query_router import QueryRouter, create_default_model_configs
from prompts import SYSTEM_TEMPLATE, USER_TEMPLATE, PLANNER_SYSTEM, PLANNER_USER, JUDGE_SYSTEM, JUDGE_USER, SIMPLE_SYSTEM_TEMPLATE, SIMPLE_USER_TEMPLATE, FILE_ANALYSIS_TEMPLATE
from utils import make_context, apply_unified_diff
from file_detector import CursorStyleFileDetector


def parse_simple_response(text: str) -> dict:
    """Parse simple text response from small models into structured format."""
    lines = text.strip().split('\n')
    analysis = ""
    plan = ""
    changes = []
    
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if line.startswith("Analysis:"):
            if current_section and current_content:
                if current_section == "analysis":
                    analysis = "\n".join(current_content)
                elif current_section == "plan":
                    plan = "\n".join(current_content)
            current_section = "analysis"
            current_content = [line.replace("Analysis:", "").strip()]
        elif line.startswith("Plan:"):
            if current_section and current_content:
                if current_section == "analysis":
                    analysis = "\n".join(current_content)
                elif current_section == "plan":
                    plan = "\n".join(current_content)
            current_section = "plan"
            current_content = [line.replace("Plan:", "").strip()]
        elif line.startswith("Changes:"):
            if current_section and current_content:
                if current_section == "analysis":
                    analysis = "\n".join(current_content)
                elif current_section == "plan":
                    plan = "\n".join(current_content)
            current_section = "changes"
            current_content = [line.replace("Changes:", "").strip()]
        elif line and current_section:
            current_content.append(line)
    
    # Handle the last section
    if current_section and current_content:
        if current_section == "analysis":
            analysis = "\n".join(current_content)
        elif current_section == "plan":
            plan = "\n".join(current_content)
        elif current_section == "changes":
            changes_text = "\n".join(current_content)
            # Try to extract individual changes
            if changes_text:
                changes = [{"path": "unknown", "rationale": changes_text, "diff": ""}]
    
    # If no structured content found, use the whole text as analysis
    if not analysis and not plan and not changes:
        analysis = text
    
    return {
        "analysis": analysis,
        "plan": plan,
        "changes": changes
    }


def create_app(
        repo_root: str,
        models: List[str],
        primary_model: str,
        embed_model: str,
        max_chunk: int,
        overlap: int,
        device: str,
        disable_apply: bool,
        planner_model: Optional[str] = None,
        judge_model: Optional[str] = None,
        num_samples: int = 2,
        max_loops: int = 2,
        quantize: bool = False,
        max_model_len: int = 1024,
        use_persistent_index: bool = True,
        shibudb_host: str = "localhost",
        shibudb_port: int = 4444,
        force_rebuild: bool = False,
        enable_routing: bool = True,
):
    # Choose indexer based on configuration
    if use_persistent_index:
        indexer = PersistentRepoIndexer(
            repo_root=repo_root,
            embed_model_name=embed_model,
            max_chunk_chars=max_chunk,
            overlap=overlap,
            shibudb_host=shibudb_host,
            shibudb_port=shibudb_port
        )
    else:
        indexer = RepoIndexer(repo_root, embed_model, max_chunk_chars=max_chunk, overlap=overlap)
    
    # Build index (incremental for persistent, full for regular)
    indexer.build(force_rebuild=force_rebuild)
    
    # Load multiple models for intelligent routing
    loaded_models = {}
    model_configs = create_default_model_configs()
    
    console.print(f"[bold cyan]Loading {len(models)} models for intelligent routing...[/]")
    for model_name in models:
        try:
            console.print(f"[blue]Loading model:[/] {model_name}")
            loaded_models[model_name] = LocalCoder(
                model_name=model_name, 
                device=device, 
                max_model_len=max_model_len, 
                quantize=quantize
            )
            console.print(f"[green]✅ Loaded:[/] {model_name}")
        except Exception as e:
            console.print(f"[red]❌ Failed to load {model_name}:[/] {e}")
            console.print(f"[yellow]Continuing with other models...[/]")
    
    if not loaded_models:
        raise RuntimeError("No models could be loaded!")
    
    # Set up query router
    router = QueryRouter(model_configs) if enable_routing else None
    
    # Set up Cursor-style file detector
    file_detector = CursorStyleFileDetector(repo_root)
    
    # Set primary model
    if primary_model and primary_model in loaded_models:
        coder = loaded_models[primary_model]
    else:
        coder = list(loaded_models.values())[0]  # Use first available model
    
    # Set up planner and judge models
    planner = loaded_models.get(planner_model or primary_model, coder)
    judge = loaded_models.get(judge_model or primary_model, coder)
    
    console.print(f"[green]✅ Primary model:[/] {coder.model_name}")
    console.print(f"[green]✅ Available models:[/] {list(loaded_models.keys())}")
    if router:
        console.print(f"[green]✅ Query routing enabled[/]")

    app = FastAPI(title="RepoCoder API", version="1.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "repo": repo_root, "model": model_name}
    
    @app.get("/stats")
    def get_stats():
        if hasattr(indexer, 'get_stats'):
            return indexer.get_stats()
        else:
            return {"status": "ok", "files_indexed": len(indexer.chunks), "indexer_type": "in-memory"}

    @app.post("/index")
    def reindex(req: IndexRequest):
        nonlocal indexer
        root = req.folder or repo_root
        
        if use_persistent_index:
            new_indexer = PersistentRepoIndexer(
                repo_root=root,
                embed_model_name=embed_model,
                max_chunk_chars=max_chunk,
                overlap=overlap,
                shibudb_host=shibudb_host,
                shibudb_port=shibudb_port
            )
        else:
            new_indexer = RepoIndexer(root, embed_model, max_chunk_chars=max_chunk, overlap=overlap)
        
        new_indexer.build(force_rebuild=True)
        indexer = new_indexer
        
        if hasattr(indexer, 'get_stats'):
            stats = indexer.get_stats()
            return {"status": "ok", "stats": stats}
        else:
            return {"status": "ok", "files_indexed": len(indexer.chunks)}

    @app.post("/query", response_model=QueryResponse)
    def query(req: QueryRequest):
        t0 = time.time()
        
        # Cursor-style file detection
        query_analysis = file_detector.detect_files_in_query(req.prompt)
        console.print(f"[blue]Query Analysis:[/] {query_analysis.query_type}")
        
        if query_analysis.has_file_references:
            console.print(f"[green]Detected {len(query_analysis.file_references)} file reference(s):[/]")
            for ref in query_analysis.file_references:
                console.print(f"  📄 {ref.filename} (confidence: {ref.confidence:.2f})")
        
        # Intelligent query routing
        if router and len(loaded_models) > 1:
            selected_model_name, intent = router.route_query(req.prompt, list(loaded_models.keys()))
            selected_model = loaded_models[selected_model_name]
            console.print(f"[blue]Routing query to:[/] {selected_model_name} ({intent.query_type.value})")
        else:
            selected_model = coder
            selected_model_name = coder.model_name
            intent = None
        
        # Cursor-style retrieval based on file references
        if query_analysis.has_file_references:
            # Retrieve chunks from specific files
            chunks = []
            for file_ref in query_analysis.file_references:
                file_chunks = indexer.retrieve_by_file(file_ref.filename, top_k=req.top_k)
                chunks.extend(file_chunks)
            
            # If no file-specific chunks found, fall back to semantic search
            if not chunks:
                console.print("[yellow]No file-specific chunks found, using semantic search[/]")
                chunks = indexer.retrieve(req.prompt, top_k=req.top_k)
        else:
            # Regular semantic retrieval
            chunks = indexer.retrieve(req.prompt, top_k=req.top_k)
        
        # Enhanced context building with file references
        context = make_context(chunks, indexer.repo_root, query_analysis.file_references)
        
        # Use appropriate prompts based on model size and query type
        if selected_model.max_model_len <= 1024:
            system = SIMPLE_SYSTEM_TEMPLATE
            user = SIMPLE_USER_TEMPLATE.format(task=req.prompt, context=context[:2000])  # Limit context
        else:
            system = SYSTEM_TEMPLATE
            # Use file-specific template for file analysis queries
            if query_analysis.query_type == "file_analysis":
                user = FILE_ANALYSIS_TEMPLATE.format(task=req.prompt, context=context)
            else:
                user = USER_TEMPLATE.format(task=req.prompt, k=req.top_k, context=context)
        
        # Ensure max_new_tokens doesn't exceed model capacity
        safe_max_tokens = min(req.max_new_tokens, selected_model.max_model_len // 2)
        out = selected_model.chat(system=system, user=user, max_new_tokens=safe_max_tokens, temperature=req.temperature)
        
        # Try to parse JSON strictly; if it fails, wrap as analysis-only
        try:
            parsed = json.loads(out)
        except Exception:
            # For small models, try to extract structured information from text
            if selected_model.max_model_len <= 1024:
                parsed = parse_simple_response(out)
            else:
                parsed = {"analysis": out, "plan": "", "changes": []}
        
        # Add routing and file detection information to response
        if intent:
            parsed["routing"] = {
                "selected_model": selected_model_name,
                "query_type": intent.query_type.value,
                "complexity": intent.complexity,
                "confidence": intent.confidence,
                "reasoning": intent.reasoning
            }
        
        # Add file detection information (Cursor-style)
        if query_analysis.has_file_references:
            parsed["file_references"] = [
                {
                    "filename": ref.filename,
                    "confidence": ref.confidence,
                    "context": ref.context,
                    "line_number": ref.line_number
                }
                for ref in query_analysis.file_references
            ]
        
        took_ms = int((time.time() - t0) * 1000)
        return QueryResponse(model=selected_model_name, took_ms=took_ms, retrieved=len(chunks), result=parsed)

    @app.post("/query_plus", response_model=QueryResponse)
    def query_plus(req: QueryRequest):
        """Planner → generate N candidates → judge → iterate up to max_loops or early-stop."""
        t0 = time.time()
        # 1) Initial retrieval for planner context
        base_k = max(6, req.top_k or 12)
        base_chunks = indexer.retrieve(req.prompt, top_k=base_k) if base_k > 0 else []
        planner_ctx = make_context(base_chunks, indexer.repo_root)
        plan_user = PLANNER_USER.format(task=req.prompt, k=len(base_chunks)) + "\n\n" + planner_ctx
        spec = planner.chat(system=PLANNER_SYSTEM, user=plan_user, max_new_tokens=800, temperature=0.2)
        try:
            spec_json = json.loads(spec)
        except Exception:
            spec_json = {"goal": req.prompt, "target_signals": [], "constraints": [], "acceptance": "", "hint_paths": []}

        best: Tuple[int, Dict[str, Any], Dict[str, Any]] = (0, {"analysis": "No candidate", "plan": "", "changes": []}, {"verdict": "fail"})

        loops = max(1, min(max_loops, 5))
        samples = max(1, min(num_samples, 5))

        def refine_query() -> str:
            sig = " ".join(spec_json.get("target_signals", [])[:10])
            return (req.prompt + "\n" + sig).strip()

        for _ in range(loops):
            # 2) Refined retrieval using planner signals
            q = refine_query()
            tk = max(12, req.top_k or 12)
            chunks = indexer.retrieve(q, top_k=tk) if tk > 0 else []
            context = make_context(chunks, indexer.repo_root)
            user = USER_TEMPLATE.format(task=req.prompt, k=len(chunks), context=context)

            # 3) Generate N candidate patches
            cands: List[Dict[str, Any]] = []
            for _s in range(samples):
                # Ensure max_new_tokens doesn't exceed model capacity
                safe_max_tokens = min(req.max_new_tokens, coder.max_model_len // 2)
                out = coder.chat(system=SYSTEM_TEMPLATE, user=user, max_new_tokens=safe_max_tokens, temperature=req.temperature)
                try:
                    parsed = json.loads(out)
                except Exception:
                    parsed = {"analysis": out, "plan": "", "changes": []}
                cands.append(parsed)

            # 4) Judge each candidate
            judged: List[Tuple[int, Dict[str, Any], Dict[str, Any]]] = []
            for cand in cands:
                changes_str = json.dumps(cand.get("changes", []))[:24000]
                spec_str = json.dumps(spec_json)[:8000]
                verdict = judge.chat(system=JUDGE_SYSTEM, user=JUDGE_USER.format(spec=spec_str, changes=changes_str), max_new_tokens=300, temperature=0.0)
                try:
                    vjson = json.loads(verdict)
                except Exception:
                    vjson = {"score": 0, "verdict": "fail", "reasons": verdict, "risks": ""}
                judged.append((int(vjson.get("score", 0)), cand, vjson))

            judged.sort(key=lambda x: x[0], reverse=True)
            top = judged[0]
            if top[0] > best[0]:
                best = top
            # Early stop if high confidence
            if best[0] >= 85:
                break

        took_ms = int((time.time() - t0) * 1000)
        score, cand, verdict = best
        result = {
            "analysis": cand.get("analysis", ""),
            "plan": cand.get("plan", ""),
            "changes": cand.get("changes", []),
            "planner_spec": spec_json,
            "judge": {"score": score, **verdict}
        }
        return QueryResponse(model=model_name, took_ms=took_ms, retrieved=len(base_chunks), result=result)

    if not disable_apply:
        @app.post("/apply")
        def apply(req: ApplyRequest):
            try:
                changed = apply_unified_diff(indexer.repo_root, req.diff)
                return {"status": "ok", "changed": changed}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    else:
        @app.post("/apply")
        def apply_disabled(_: ApplyRequest):
            raise HTTPException(status_code=403, detail="/apply is disabled. Start without --disable-apply to enable.")

    return app


if __name__ == "__main__":
    args = parse_args()
    repo_root = args.repo
    if not os.path.isdir(repo_root):
        print(f"Repo path not found: {repo_root}")
        sys.exit(1)

    # Apply environment defaults if needed
    env_defaults = get_environment_defaults(args.environment)
    
    # Use environment defaults for unspecified parameters
    models = args.models if args.models else env_defaults["models"]
    primary_model = args.primary_model or env_defaults["primary_model"]
    max_model_len = args.max_model_len if args.max_model_len != 1024 else env_defaults["max_model_len"]
    device = args.device if args.device != "cpu" else env_defaults["device"]
    quantize = args.quantize or env_defaults["quantize"]
    max_chunk = args.max_chunk_chars if args.max_chunk_chars != 800 else env_defaults["max_chunk_chars"]
    overlap = args.chunk_overlap if args.chunk_overlap != 100 else env_defaults["chunk_overlap"]

    app = create_app(
        repo_root=repo_root,
        models=models,
        primary_model=primary_model,
        embed_model=args.embed_model,
        max_chunk=max_chunk,
        overlap=overlap,
        device=device,
        disable_apply=args.disable_apply,
        planner_model=args.planner_model,
        judge_model=args.judge_model,
        num_samples=args.num_samples,
        max_loops=args.max_loops,
        quantize=quantize,
        max_model_len=max_model_len,
        use_persistent_index=args.use_persistent_index,
        shibudb_host=args.shibudb_host,
        shibudb_port=args.shibudb_port,
        force_rebuild=args.force_rebuild,
        enable_routing=args.enable_routing,
    )

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)