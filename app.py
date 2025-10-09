#!/usr/bin/env python3
"""
RepoCoder - Intelligent Code Analysis System

A modular pipeline that:
1. Indexes code (file tree + vector storage)
2. Understands queries (file detection + intent classification)
3. Retrieves relevant context (smart retrieval strategies)
4. Selects appropriate models (based on query intent)
5. Generates intelligent responses

Can use LLMs at any stage for better understanding.
"""

import os
import sys
import argparse
from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rich.console import Console

# Import core components
from core.pipeline import RepoCoderPipeline
from core.types import ModelConfig

# Import config
from config import CODE_EXTS, IGNORE_DIRS

# Import LLM executor
from llm import LocalCoder

console = Console()


# API Models
class QueryRequest(BaseModel):
    prompt: str
    top_k: int = 20


class QueryResponse(BaseModel):
    model: str
    took_ms: int
    retrieved: int
    result: Dict
    query_analysis: Dict
    retrieval: Dict


def create_models_config(models: List[str], device: str, max_model_len: int) -> Dict[str, ModelConfig]:
    """Create model configurations with capabilities"""
    
    # Model capabilities mapping
    capability_map = {
        "Qwen/Qwen2.5-Coder-7B-Instruct": ["code_analysis", "code_generation", "debugging", "code_review"],
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct": ["code_analysis", "code_generation", "debugging"],
        "codellama/CodeLlama-7b-Instruct-hf": ["code_analysis", "code_generation"],
        "microsoft/DialoGPT-small": ["general_qa"],
        "microsoft/DialoGPT-large": ["general_qa", "code_analysis"],
    }
    
    model_configs = {}
    for model_name in models:
        capabilities = capability_map.get(model_name, ["general_qa"])
        model_type = "code" if "code" in model_name.lower() or "coder" in model_name.lower() else "general"
        
        model_configs[model_name] = ModelConfig(
            name=model_name,
            type=model_type,
            capabilities=capabilities,
            max_tokens=max_model_len,
            temperature=0.2,
            device=device
        )
    
    return model_configs


def create_app(repo_root: str, models: List[str], device: str = "cpu", 
               max_model_len: int = 4096, embed_model: str = "sentence-transformers/all-MiniLM-L6-v2",
               use_llm_routing: bool = False, routing_model: str = None):
    """Create the RepoCoder FastAPI application"""
    
    console.print("[bold cyan]═══ RepoCoder Starting ═══[/]")
    
    # Load embedding model
    console.print(f"[blue]Loading embedding model:[/] {embed_model}")
    from sentence_transformers import SentenceTransformer
    import torch
    embedder = SentenceTransformer(
        embed_model, 
        device="cuda" if torch.cuda.is_available() and device != "cpu" else "cpu"
    )
    console.print("[green]✓ Embedding model loaded[/]")
    
    # Load LLM for response generation
    console.print(f"[blue]Loading primary LLM:[/] {models[0]}")
    llm_executor = LocalCoder(model_name=models[0], device=device, max_model_len=max_model_len)
    console.print("[green]✓ LLM loaded[/]")
    
    # Optionally load small LLM for routing
    routing_llm = None
    if use_llm_routing:
        routing_model_name = routing_model or "microsoft/DialoGPT-small"
        console.print(f"[blue]Loading routing LLM:[/] {routing_model_name}")
        routing_llm = LocalCoder(model_name=routing_model_name, device=device, max_model_len=1024)
        console.print("[green]✓ Routing LLM loaded[/]")
    
    # Create model configs
    model_configs = create_models_config(models, device, max_model_len)
    
    # Initialize the main pipeline
    pipeline = RepoCoderPipeline(
        repo_root=repo_root,
        code_extensions=CODE_EXTS,
        ignore_dirs=IGNORE_DIRS,
        models=model_configs,
        embedder=embedder,
        llm_executor=llm_executor,
        routing_llm=routing_llm,
        use_llm_routing=use_llm_routing
    )
    
    # Build the index
    pipeline.build_index()
    
    # Create FastAPI app
    app = FastAPI(title="RepoCoder API", version="2.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        """Health check endpoint"""
        return {"status": "ok", "version": "2.0.0", "repo": repo_root}
    
    @app.get("/stats")
    def get_stats():
        """Get indexing and system statistics"""
        return pipeline.get_stats()
    
    # Import agents
    from agents.planner import PlannerAgent
    from agents.coder import CoderAgent
    from agents.judge import JudgeAgent
    from agents.executor import ExecutorAgent
    from agents.orchestrator import AgentOrchestrator
    
    # Initialize agents
    planner = PlannerAgent(llm_executor, pipeline.context_retriever, pipeline.indexer)
    coder = CoderAgent(llm_executor, pipeline.context_retriever, pipeline.indexer, repo_root)
    judge = JudgeAgent(llm_executor)
    executor = ExecutorAgent(repo_root, auto_commit=False, auto_pr=False)
    orchestrator = AgentOrchestrator(planner, coder, judge, executor)

    @app.post("/query", response_model=QueryResponse)
    def query(req: QueryRequest):
        """
        Process a code query through the intelligent pipeline
        
        The pipeline:
        1. Analyzes the query (detects files, intent, entities)
        2. Retrieves relevant context (file-specific or semantic)
        3. Selects the best model for the task
        4. Generates an intelligent response
        """
        try:
            result = pipeline.query(req.prompt, req.top_k)
            return QueryResponse(**result)
        except Exception as e:
            console.print(f"[red]Error processing query:[/] {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/implement")
    def implement_feature(req: QueryRequest):
        """
        Multi-agent feature implementation (Cursor-style)
        
        Process:
        1. PLANNER: Creates detailed plan
        2. CODER: Implements each step
        3. JUDGE: Reviews each change
        4. EXECUTOR: Applies changes (optional)
        
        This is for code modification requests like:
        - "Add rate limiting to API with tests"
        - "Implement user authentication following project style"
        - "Refactor database layer and add error handling"
        """
        try:
            # Analyze the query first
            from core.query_analyzer import QueryAnalyzer
            analyzer = QueryAnalyzer()
            query_analysis = analyzer.analyze(req.prompt)
            
            # Execute through multi-agent workflow
            result = orchestrator.execute_feature_request(
                user_request=req.prompt,
                query_analysis=query_analysis,
                auto_apply=False  # Don't auto-apply (return plan only)
            )
            
            return {
                "model": "MultiAgent",
                "took_ms": 0,  # TODO: Track timing
                "result": result
            }
            
        except Exception as e:
            console.print(f"[red]Error in multi-agent workflow:[/] {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    console.print("\n[bold green]═══ RepoCoder Ready! ═══[/]")
    console.print(f"[cyan]Repository:[/] {repo_root}")
    console.print(f"[cyan]Models:[/] {', '.join(models)}")
    console.print(f"[cyan]API Endpoints:[/]")
    console.print(f"  • GET  /health - Health check")
    console.print(f"  • GET  /stats - Repository statistics")
    console.print(f"  • POST /query - Code analysis (simple)")
    console.print(f"  • POST /implement - Feature implementation (multi-agent)")
    console.print(f"[cyan]Docs:[/] http://localhost:8000/docs")

    return app


def parse_args():
    """Parse command line arguments"""
    p = argparse.ArgumentParser(description="RepoCoder - Intelligent Code Analysis API")
    
    # Required
    p.add_argument("--repo", required=True, help="Path to the code repository to index")
    
    # Server config
    p.add_argument("--host", default="127.0.0.1", help="Server host")
    p.add_argument("--port", type=int, default=8000, help="Server port")
    
    # Models
    p.add_argument("--models", nargs="+", 
                   default=["Qwen/Qwen2.5-Coder-7B-Instruct"],
                   help="Models to load (first is primary)")
    p.add_argument("--embed-model", 
                   default="sentence-transformers/all-MiniLM-L6-v2",
                   help="Embedding model for vector search")
    
    # Intelligent Routing
    p.add_argument("--use-llm-routing", action="store_true",
                   help="Use small LLM for intelligent query routing (slower but smarter)")
    p.add_argument("--routing-model", default="microsoft/DialoGPT-small",
                   help="Small model to use for query routing")
    
    # Hardware
    p.add_argument("--device", default="cpu", 
                   help="Device to use (cpu/cuda/auto)")
    p.add_argument("--max-model-len", type=int, default=4096,
                   help="Maximum context length for models")
    
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Validate repository path
    repo_root = args.repo
    if not os.path.isdir(repo_root):
        console.print(f"[red]Error: Repository path not found:[/] {repo_root}")
        sys.exit(1)
    
    # Create and run the app
    app = create_app(
        repo_root=repo_root,
        models=args.models,
        device=args.device,
        max_model_len=args.max_model_len,
        embed_model=args.embed_model,
        use_llm_routing=args.use_llm_routing,
        routing_model=args.routing_model
    )

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
