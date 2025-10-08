"""
Intelligent Query Router - Decides what data/strategy to use
Can use a small LLM to understand query intent better
"""

import re
from typing import Dict, Any, Optional
from rich.console import Console

from .types import QueryAnalysis, IntentType

console = Console()


class QueryRouter:
    """
    Routes queries to appropriate data sources and strategies.
    
    Determines:
    1. Does query need code chunks? (vector search)
    2. Does query need metadata? (file tree, stats)
    3. Does query need both?
    4. Should we use direct computation?
    """
    
    def __init__(self, indexer, use_llm: bool = False, llm=None):
        self.indexer = indexer
        self.use_llm = use_llm
        self.llm = llm
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize patterns for different query types"""
        
        # Metadata-only queries (no code needed)
        self.metadata_patterns = [
            r'\bhow many.*files?\b',
            r'\bcount.*files?\b',
            r'\blist.*files?\b',
            r'\bwhat.*files?\b',
            r'\bhow many.*lines?\b',
            r'\bcount.*lines?\b',
            r'\bproject.*size\b',
            r'\brepository.*size\b',
            r'\bwhat.*languages?\b',
            r'\bhow many.*languages?\b',
            r'\bfile.*types?\b',
            r'\bproject.*structure\b',
            r'\bdirectory.*structure\b',
        ]
        
        # File tree queries (need structure, minimal code)
        self.structure_patterns = [
            r'\bproject.*organization\b',
            r'\bfile.*organization\b',
            r'\bwhere.*is.*located\b',
            r'\bfind.*file\b',
            r'\bwhich.*directory\b',
        ]
        
        # Direct computation queries (no LLM needed)
        self.computation_patterns = [
            r'\bhow many\b',
            r'\bcount\b',
            r'\btotal\b',
            r'\bsum\b',
            r'\baverage\b',
        ]
    
    def route(self, query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """
        Route query to appropriate strategy
        
        Returns:
            routing_decision: {
                "strategy": "metadata" | "structure" | "code" | "hybrid",
                "needs_code": bool,
                "needs_metadata": bool,
                "can_compute_directly": bool,
                "reasoning": str
            }
        """
        
        console.print(f"[cyan]→ Routing query: '{query_analysis.original_query}'[/]")
        
        query_lower = query_analysis.normalized_query
        
        # Check if this is a metadata-only query
        if self._is_metadata_query(query_lower):
            decision = {
                "strategy": "metadata",
                "needs_code": False,
                "needs_metadata": True,
                "can_compute_directly": True,
                "reasoning": "Query asks for repository metadata/statistics"
            }
            console.print(f"[green]✓ Routed to: METADATA strategy[/]")
            return decision
        
        # Check if this is a structure query
        if self._is_structure_query(query_lower):
            decision = {
                "strategy": "structure",
                "needs_code": False,
                "needs_metadata": True,
                "can_compute_directly": False,
                "reasoning": "Query asks about project structure"
            }
            console.print(f"[green]✓ Routed to: STRUCTURE strategy[/]")
            return decision
        
        # Check if this is a direct computation
        if self._is_computation_query(query_lower):
            decision = {
                "strategy": "metadata",
                "needs_code": False,
                "needs_metadata": True,
                "can_compute_directly": True,
                "reasoning": "Query needs simple computation from metadata"
            }
            console.print(f"[green]✓ Routed to: METADATA (computation) strategy[/]")
            return decision
        
        # If files are explicitly mentioned, use file-specific strategy
        if query_analysis.file_references:
            decision = {
                "strategy": "file_specific",
                "needs_code": True,
                "needs_metadata": False,
                "can_compute_directly": False,
                "reasoning": f"User mentioned specific file(s): {[r.filename for r in query_analysis.file_references]}"
            }
            console.print(f"[green]✓ Routed to: FILE_SPECIFIC strategy[/]")
            return decision
        
        # Default: use semantic code search
        decision = {
            "strategy": "semantic",
            "needs_code": True,
            "needs_metadata": False,
            "can_compute_directly": False,
            "reasoning": "General code query, using semantic search"
        }
        console.print(f"[green]✓ Routed to: SEMANTIC strategy[/]")
        return decision
    
    def _is_metadata_query(self, query: str) -> bool:
        """Check if query is asking for metadata"""
        for pattern in self.metadata_patterns:
            if re.search(pattern, query):
                return True
        return False
    
    def _is_structure_query(self, query: str) -> bool:
        """Check if query is asking about structure"""
        for pattern in self.structure_patterns:
            if re.search(pattern, query):
                return True
        return False
    
    def _is_computation_query(self, query: str) -> bool:
        """Check if query needs simple computation"""
        for pattern in self.computation_patterns:
            if re.search(pattern, query):
                return True
        return False
    
    def answer_metadata_query(self, query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """Answer metadata queries directly without LLM"""
        
        console.print("[cyan]→ Answering metadata query directly from file tree[/]")
        
        stats = self.indexer.get_stats()
        query_lower = query_analysis.normalized_query
        
        # Build direct answer based on query
        if "how many files" in query_lower or "count files" in query_lower:
            answer = f"The project has {stats['total_files']} files, of which {stats['code_files']} are code files."
        
        elif "how many lines" in query_lower or "count lines" in query_lower:
            # Calculate total lines
            total_lines = sum(chunk.end_line for chunk in self.indexer.chunks)
            answer = f"The project has approximately {total_lines:,} lines of code across {stats['code_files']} files."
        
        elif "what languages" in query_lower or "how many languages" in query_lower:
            # Get unique languages
            languages = set(f.language for f in self.indexer.file_tree if f.language)
            answer = f"The project uses {stats['languages']} programming languages: {', '.join(sorted(languages))}."
        
        elif "project size" in query_lower or "repository size" in query_lower:
            total_size = sum(f.size for f in self.indexer.file_tree)
            answer = f"The project size is {total_size / 1024 / 1024:.2f} MB across {stats['total_files']} files."
        
        elif "list files" in query_lower:
            files = [f.name for f in self.indexer.file_tree[:20]]
            answer = f"Here are the files in the project: {', '.join(files)}"
            if len(self.indexer.file_tree) > 20:
                answer += f" ... and {len(self.indexer.file_tree) - 20} more."
        
        else:
            # Generic metadata answer
            answer = f"Project statistics: {stats['total_files']} files, {stats['code_files']} code files, {stats['languages']} languages, {stats['total_chunks']} code chunks."
        
        console.print(f"[green]✓ Direct answer: {answer}[/]")
        
        return {
            "analysis": answer,
            "plan": "Direct computation from file tree metadata",
            "changes": [],
            "metadata": {
                "direct_answer": True,
                "stats": stats
            }
        }

