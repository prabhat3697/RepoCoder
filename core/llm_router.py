"""
LLM-Based Query Router - Uses a small, fast model to make intelligent routing decisions
"""

import json
from typing import Dict, Any, Optional
from rich.console import Console

from .types import QueryAnalysis

console = Console()


class LLMQueryRouter:
    """
    Uses a small LLM to intelligently route queries.
    
    Much better than regex patterns because it understands:
    - Context and nuance
    - Complex queries
    - Multi-intent queries
    - Ambiguous cases
    """
    
    def __init__(self, indexer, small_llm=None):
        self.indexer = indexer
        self.small_llm = small_llm
        
        # Ultra-simple routing prompt - just ask for ONE WORD
        self.routing_prompt = """You are a routing classifier. Return ONLY ONE WORD.

If query asks about file counts, languages, or project stats → say "metadata"
If query mentions a specific filename → say "file_specific"
If query asks about project structure or organization → say "structure"
Otherwise → say "semantic"

Return ONLY the category word, nothing else."""
    
    def route(self, query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """Route query using small LLM for intelligent decision"""
        
        console.print(f"[cyan]→ Using LLM to route query...[/]")
        
        if not self.small_llm:
            console.print("[yellow]⚠ No LLM available, using fallback routing[/]")
            return self._fallback_route(query_analysis)
        
        # Build ultra-simple query - just need the category
        files_mentioned = [r.filename for r in query_analysis.file_references] if query_analysis.file_references else []
        
        # Give hints to the model
        if files_mentioned:
            file_hint = f" (mentions {', '.join(files_mentioned)})"
        else:
            file_hint = ""
        
        user_query = f""""{query_analysis.original_query}"{file_hint}

Answer with ONE word:"""
        
        try:
            # Use small LLM to make routing decision
            console.print("[cyan]→ Asking small LLM for routing decision...[/]")
            
            output = self.small_llm.chat(
                system=self.routing_prompt,
                user=user_query,
                max_new_tokens=10,  # Just need one word!
                temperature=0.0  # Deterministic routing
            )
            
            # Parse simple one-word response
            decision = self._parse_simple_decision(output, query_analysis)
            
            console.print(f"[green]✓ LLM routing decision:[/] {decision['strategy']}")
            console.print(f"  Reasoning: {decision['reasoning']}")
            
            return decision
            
        except Exception as e:
            console.print(f"[yellow]⚠ LLM routing failed: {e}, using fallback[/]")
            return self._fallback_route(query_analysis)
    
    def _parse_simple_decision(self, output: str, query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """Parse simple one-word LLM decision"""
        
        # Clean the output
        output_clean = output.strip().lower()
        
        console.print(f"[cyan]→ LLM output: '{output_clean}'[/]")
        
        # Extract the strategy word
        strategy = None
        for word in ["metadata", "file_specific", "semantic", "structure"]:
            if word.replace("_", "") in output_clean.replace("_", "").replace("-", "").replace(" ", ""):
                strategy = word
                break
        
        if not strategy:
            # Try to find any of the keywords
            if "metadata" in output_clean or "meta" in output_clean:
                strategy = "metadata"
            elif "file" in output_clean or "specific" in output_clean:
                strategy = "file_specific"
            elif "structure" in output_clean or "organization" in output_clean:
                strategy = "structure"
            else:
                strategy = "semantic"
        
        console.print(f"[green]✓ Detected strategy: {strategy}[/]")
        
        # Build decision based on strategy
        if strategy == "metadata":
            return {
                "strategy": "metadata",
                "needs_code": False,
                "needs_metadata": True,
                "can_compute_directly": True,
                "confidence": 0.9,
                "reasoning": "LLM classified as metadata query"
            }
        elif strategy == "file_specific":
            return {
                "strategy": "file_specific",
                "needs_code": True,
                "needs_metadata": False,
                "can_compute_directly": False,
                "confidence": 0.9,
                "reasoning": f"LLM detected file-specific query for: {[r.filename for r in query_analysis.file_references]}"
            }
        elif strategy == "structure":
            return {
                "strategy": "structure",
                "needs_code": False,
                "needs_metadata": True,
                "can_compute_directly": False,
                "confidence": 0.8,
                "reasoning": "LLM classified as structure query"
            }
        else:  # semantic
            return {
                "strategy": "semantic",
                "needs_code": True,
                "needs_metadata": False,
                "can_compute_directly": False,
                "confidence": 0.7,
                "reasoning": "LLM classified as semantic query"
            }
    
    def _parse_llm_decision_old(self, output: str) -> Dict[str, Any]:
        """Parse LLM routing decision"""
        
        # Extract JSON from output
        if "{" in output and "}" in output:
            start = output.find("{")
            end = output.rfind("}") + 1
            json_str = output[start:end]
            
            try:
                decision = json.loads(json_str)
                
                # Validate required fields
                if "strategy" not in decision:
                    raise ValueError("Missing 'strategy' field")
                
                # Set defaults for missing fields
                decision.setdefault("needs_code", True)
                decision.setdefault("needs_metadata", False)
                decision.setdefault("can_compute_directly", False)
                decision.setdefault("confidence", 0.5)
                decision.setdefault("reasoning", "LLM routing decision")
                
                return decision
                
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to parse LLM decision: {e}[/]")
                raise
        
        raise ValueError("No JSON found in LLM output")
    
    def _fallback_route(self, query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """Fallback routing when LLM is not available"""
        
        # Simple heuristic-based routing
        query_lower = query_analysis.normalized_query
        
        # Check for metadata keywords
        metadata_keywords = ["how many", "count", "list", "what languages", "project size"]
        if any(kw in query_lower for kw in metadata_keywords):
            return {
                "strategy": "metadata",
                "needs_code": False,
                "needs_metadata": True,
                "can_compute_directly": True,
                "confidence": 0.8,
                "reasoning": "Detected metadata keywords (fallback)"
            }
        
        # Check for file references
        if query_analysis.file_references:
            return {
                "strategy": "file_specific",
                "needs_code": True,
                "needs_metadata": False,
                "can_compute_directly": False,
                "confidence": 0.9,
                "reasoning": f"File references detected (fallback)"
            }
        
        # Default to semantic
        return {
            "strategy": "semantic",
            "needs_code": True,
            "needs_metadata": False,
            "can_compute_directly": False,
            "confidence": 0.5,
            "reasoning": "Default semantic search (fallback)"
        }
    
    def answer_metadata_query(self, query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """Answer metadata queries directly from file tree"""
        
        console.print("[cyan]→ Answering metadata query from file tree...[/]")
        
        stats = self.indexer.get_stats()
        query_lower = query_analysis.normalized_query
        
        # Use small LLM to generate better answer if available
        if self.small_llm:
            return self._llm_metadata_answer(query_analysis, stats)
        
        # Fallback: simple string formatting
        return self._simple_metadata_answer(query_lower, stats)
    
    def _llm_metadata_answer(self, query_analysis: QueryAnalysis, stats: Dict) -> Dict[str, Any]:
        """Use small LLM to answer metadata query with stats"""
        
        console.print("[cyan]→ Using small LLM to format metadata answer...[/]")
        
        # Get file samples
        file_samples = [f.name for f in self.indexer.file_tree[:10]]
        languages = set(f.language for f in self.indexer.file_tree if f.language)
        
        stats_summary = f"""Repository Statistics:
- Total Files: {stats['total_files']}
- Code Files: {stats['code_files']}
- Total Chunks: {stats['total_chunks']}
- Languages: {stats['languages']} ({', '.join(sorted(languages))})
- Sample Files: {', '.join(file_samples)}
{f"  ... and {stats['total_files'] - 10} more files" if stats['total_files'] > 10 else ""}"""
        
        prompt = f"""User Query: "{query_analysis.original_query}"

{stats_summary}

Provide a natural, helpful answer to the user's query based on these statistics.
Keep it concise and conversational."""
        
        try:
            answer = self.small_llm.chat(
                system="You are a helpful assistant that answers questions about code repositories.",
                user=prompt,
                max_new_tokens=200,
                temperature=0.3
            )
            
            return {
                "analysis": answer.strip(),
                "plan": "Direct answer from repository metadata",
                "changes": [],
                "metadata": {"stats": stats, "llm_generated": True}
            }
            
        except Exception as e:
            console.print(f"[yellow]⚠ LLM answer failed: {e}, using simple answer[/]")
            return self._simple_metadata_answer(query_analysis.normalized_query, stats)
    
    def _simple_metadata_answer(self, query: str, stats: Dict) -> Dict[str, Any]:
        """Simple metadata answer without LLM"""
        
        if "how many files" in query or "count files" in query:
            answer = f"The project has {stats['total_files']} files, of which {stats['code_files']} are code files."
        
        elif "what languages" in query:
            languages = set(f.language for f in self.indexer.file_tree if f.language)
            answer = f"The project uses {stats['languages']} programming languages: {', '.join(sorted(languages))}."
        
        elif "project size" in query:
            total_size = sum(f.size for f in self.indexer.file_tree)
            answer = f"The project size is {total_size / 1024 / 1024:.2f} MB across {stats['total_files']} files with {stats['total_chunks']} code chunks."
        
        elif "list files" in query:
            files = [f.name for f in self.indexer.file_tree[:20]]
            answer = f"Here are the files: {', '.join(files)}"
            if len(self.indexer.file_tree) > 20:
                answer += f" ... and {len(self.indexer.file_tree) - 20} more."
        
        else:
            answer = f"Project has {stats['total_files']} files ({stats['code_files']} code files), {stats['total_chunks']} chunks, {stats['languages']} languages."
        
        return {
            "analysis": answer,
            "plan": "Direct computation from file tree",
            "changes": [],
            "metadata": {"stats": stats, "direct_computation": True}
        }

