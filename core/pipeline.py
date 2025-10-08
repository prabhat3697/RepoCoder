"""
RepoCoder V2 Pipeline - Orchestrates all components
"""

import time
from typing import Dict, Any
from rich.console import Console

from .types import QueryAnalysis, RetrievalContext, Response, ModelConfig
from .indexer import CoreIndexer
from .query_analyzer import QueryAnalyzer
from .context_retriever import ContextRetriever
from .model_selector import ModelSelector
from .response_generator import ResponseGenerator
from .query_router import QueryRouter
from .llm_router import LLMQueryRouter

console = Console()


class RepoCoderPipeline:
    """
    Main pipeline that orchestrates:
    1. Query Analysis
    2. Intent Classification
    3. Context Retrieval
    4. Model Selection
    5. Response Generation
    """
    
    def __init__(self, repo_root: str, code_extensions: set, ignore_dirs: set,
                 models: Dict[str, ModelConfig], embedder=None, llm_executor=None, 
                 routing_llm=None, use_llm_routing: bool = False):
        
        console.print("[bold cyan]Initializing RepoCoder Pipeline...[/]")
        
        self.repo_root = repo_root
        self.use_llm_routing = use_llm_routing
        
        # Initialize components
        self.indexer = CoreIndexer(repo_root, code_extensions, ignore_dirs)
        self.query_analyzer = QueryAnalyzer(use_llm=False)
        
        # Choose router based on configuration
        if use_llm_routing and routing_llm:
            console.print("[cyan]→ Using LLM-based query routing (intelligent)[/]")
            self.query_router = LLMQueryRouter(self.indexer, small_llm=routing_llm)
        else:
            console.print("[cyan]→ Using pattern-based query routing (fast)[/]")
            self.query_router = QueryRouter(self.indexer, use_llm=False)
        
        self.context_retriever = ContextRetriever(self.indexer, embedder)
        self.model_selector = ModelSelector(models)
        self.response_generator = ResponseGenerator(llm_executor)
        
        console.print("[green]Pipeline initialized successfully![/]")
    
    def build_index(self):
        """Build the repository index"""
        console.print("\n[bold cyan]═══ Building Repository Index ═══[/]")
        
        # Step 1: Build file tree
        self.indexer.build_file_tree()
        
        # Step 2: Extract chunks
        self.indexer.extract_chunks()
        
        # Step 3: Compute embeddings
        self.context_retriever.compute_embeddings()
        
        # Print stats
        stats = self.indexer.get_stats()
        console.print(f"\n[bold green]✓ Index Built Successfully![/]")
        console.print(f"  Files: {stats['code_files']}/{stats['total_files']}")
        console.print(f"  Chunks: {stats['total_chunks']}")
        console.print(f"  Languages: {stats['languages']}")
    
    def query(self, query_text: str, top_k: int = 20) -> Dict[str, Any]:
        """
        Process a query through the complete pipeline
        
        Args:
            query_text: The user's query
            top_k: Number of chunks to retrieve
            
        Returns:
            Dictionary containing response and metadata
        """
        console.print(f"\n[bold cyan]═══ Processing Query ═══[/]")
        console.print(f"Query: {query_text}")
        
        t0 = time.time()
        
        # Step 1: Analyze Query
        console.print("\n[bold yellow]" + "="*80 + "[/]")
        console.print("[bold yellow]STEP 1: QUERY ANALYSIS[/]")
        console.print("[bold yellow]" + "="*80 + "[/]")
        query_analysis = self.query_analyzer.analyze(query_text)
        self._print_query_analysis(query_analysis)
        
        # Step 1.5: Route Query (decide what data to use)
        console.print("\n[bold yellow]" + "="*80 + "[/]")
        console.print("[bold yellow]STEP 1.5: QUERY ROUTING[/]")
        console.print("[bold yellow]" + "="*80 + "[/]")
        routing_decision = self.query_router.route(query_analysis)
        console.print(f"  Strategy: [cyan]{routing_decision['strategy']}[/]")
        console.print(f"  Needs Code: [cyan]{routing_decision['needs_code']}[/]")
        console.print(f"  Needs Metadata: [cyan]{routing_decision['needs_metadata']}[/]")
        console.print(f"  Direct Answer: [cyan]{routing_decision['can_compute_directly']}[/]")
        console.print(f"  Reasoning: [dim]{routing_decision['reasoning']}[/]")
        
        # If we can answer directly without LLM, do it!
        if routing_decision['can_compute_directly']:
            console.print("[green]✓ Answering directly from metadata (no LLM needed)[/]")
            direct_answer = self.query_router.answer_metadata_query(query_analysis)
            
            # Build response
            response = Response(
                analysis=direct_answer['analysis'],
                plan=direct_answer['plan'],
                changes=direct_answer['changes'],
                model_used="DirectComputation",
                took_ms=int((time.time() - t0) * 1000),
                confidence=1.0,
                metadata=direct_answer.get('metadata', {})
            )
            
            # Build result
            result = {
                "model": "DirectComputation",
                "took_ms": response.took_ms,
                "retrieved": 0,
                "result": {
                    "analysis": response.analysis,
                    "plan": response.plan,
                    "changes": response.changes,
                    "confidence": response.confidence,
                    "metadata": response.metadata
                },
                "query_analysis": {
                    "intent": query_analysis.intent.value,
                    "complexity": query_analysis.complexity.value,
                    "file_references": [
                        {"filename": ref.filename, "confidence": ref.confidence}
                        for ref in query_analysis.file_references
                    ],
                    "entities": query_analysis.entities
                },
                "retrieval": {
                    "strategy": "metadata_direct",
                    "files_involved": 0,
                    "total_chunks": 0
                },
                "routing": routing_decision
            }
            
            return result
        
        # Step 2: Retrieve Context
        console.print("\n[bold yellow]" + "="*80 + "[/]")
        console.print("[bold yellow]STEP 2: CONTEXT RETRIEVAL[/]")
        console.print("[bold yellow]" + "="*80 + "[/]")
        
        if query_analysis.file_references:
            # When user explicitly mentions files, ONLY retrieve from those files
            # Don't pollute with other files from semantic search
            console.print(f"[cyan]User mentioned specific file(s), using STRICT file-only retrieval[/]")
            context = self.context_retriever.retrieve(query_analysis, top_k)
        else:
            # No files mentioned, use semantic search
            console.print(f"[cyan]No files mentioned, using semantic retrieval[/]")
            context = self.context_retriever.retrieve(query_analysis, top_k)
        
        self._print_retrieval_context(context)
        
        # Step 3: Select Model
        console.print("\n[bold yellow]" + "="*80 + "[/]")
        console.print("[bold yellow]STEP 3: MODEL SELECTION[/]")
        console.print("[bold yellow]" + "="*80 + "[/]")
        model_config = self.model_selector.select_model(query_analysis)
        
        # Step 4: Generate Response
        console.print("\n[bold yellow]" + "="*80 + "[/]")
        console.print("[bold yellow]STEP 4: RESPONSE GENERATION[/]")
        console.print("[bold yellow]" + "="*80 + "[/]")
        response = self.response_generator.generate(
            query_analysis, context, model_config, self.repo_root
        )
        
        # Calculate total time
        took_ms = int((time.time() - t0) * 1000)
        response.took_ms = took_ms
        
        console.print(f"\n[bold green]✓ Query Processed in {took_ms}ms[/]")
        
        # Build result
        result = {
            "model": response.model_used,
            "took_ms": took_ms,
            "retrieved": context.total_chunks,
            "result": {
                "analysis": response.analysis,
                "plan": response.plan,
                "changes": response.changes,
                "confidence": response.confidence,
                "metadata": response.metadata
            },
            "query_analysis": {
                "intent": query_analysis.intent.value,
                "complexity": query_analysis.complexity.value,
                "file_references": [
                    {"filename": ref.filename, "confidence": ref.confidence}
                    for ref in query_analysis.file_references
                ],
                "entities": query_analysis.entities
            },
            "retrieval": {
                "strategy": context.strategy_used,
                "files_involved": len(context.file_tree),
                "total_chunks": context.total_chunks
            },
            "routing": routing_decision  # Add routing decision to response
        }
        
        return result
    
    def _print_query_analysis(self, analysis: QueryAnalysis):
        """Print query analysis details"""
        console.print(f"  Intent: [cyan]{analysis.intent.value}[/]")
        console.print(f"  Complexity: [cyan]{analysis.complexity.value}[/]")
        console.print(f"  Confidence: [cyan]{analysis.confidence:.2f}[/]")
        
        if analysis.file_references:
            console.print(f"  Files detected: {len(analysis.file_references)}")
            for ref in analysis.file_references:
                console.print(f"    • {ref.filename} (confidence: {ref.confidence:.2f})")
        
        if analysis.entities:
            entities_str = ", ".join(analysis.entities[:5])
            console.print(f"  Entities: {entities_str}")
    
    def _print_retrieval_context(self, context: RetrievalContext):
        """Print retrieval context details"""
        console.print(f"  Strategy: [cyan]{context.strategy_used}[/]")
        console.print(f"  Chunks retrieved: [cyan]{context.total_chunks}[/]")
        console.print(f"  Files involved: [cyan]{len(context.file_tree)}[/]")
        
        if context.file_tree:
            for file_node in context.file_tree[:3]:  # Show first 3
                console.print(f"    • {file_node.name}")
            if len(context.file_tree) > 3:
                console.print(f"    ... and {len(context.file_tree) - 3} more")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        indexer_stats = self.indexer.get_stats()
        model_list = self.model_selector.list_models()
        
        return {
            "repo_root": self.repo_root,
            "indexer": indexer_stats,
            "models_available": len(model_list),
            "models": model_list
        }

