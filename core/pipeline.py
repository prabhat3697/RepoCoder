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
                 models: Dict[str, ModelConfig], embedder=None, llm_executor=None):
        
        console.print("[bold cyan]Initializing RepoCoder V2 Pipeline...[/]")
        
        self.repo_root = repo_root
        
        # Initialize components
        self.indexer = CoreIndexer(repo_root, code_extensions, ignore_dirs)
        self.query_analyzer = QueryAnalyzer(use_llm=False)
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
        console.print("\n[yellow]→ Step 1: Query Analysis[/]")
        query_analysis = self.query_analyzer.analyze(query_text)
        self._print_query_analysis(query_analysis)
        
        # Step 2: Retrieve Context
        console.print("\n[yellow]→ Step 2: Context Retrieval[/]")
        if query_analysis.file_references:
            # Use hybrid retrieval for file-specific queries
            context = self.context_retriever.retrieve_hybrid(query_analysis, top_k)
        else:
            # Use standard retrieval
            context = self.context_retriever.retrieve(query_analysis, top_k)
        self._print_retrieval_context(context)
        
        # Step 3: Select Model
        console.print("\n[yellow]→ Step 3: Model Selection[/]")
        model_config = self.model_selector.select_model(query_analysis)
        
        # Step 4: Generate Response
        console.print("\n[yellow]→ Step 4: Response Generation[/]")
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
            }
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

