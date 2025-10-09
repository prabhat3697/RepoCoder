"""
Multi-Intent Query Handler
Handles queries that need multiple types of information
"""

import re
from typing import Dict, Any, List, Tuple
from rich.console import Console

from .types import QueryAnalysis

console = Console()


class MultiIntentHandler:
    """
    Handles complex queries that need multiple intents:
    - "How many files are there and how are they connected?"
    - "List all Ruby files and explain the main one"
    - "Count API endpoints and show me the authentication one"
    """
    
    def __init__(self, indexer):
        self.indexer = indexer
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize patterns for detecting multi-intent queries"""
        
        # Conjunction words that indicate multiple intents
        self.conjunction_words = [
            r'\band\b',
            r'\balso\b', 
            r'\bthen\b',
            r'\bplus\b',
            r'\bafter that\b',
            r'\badditionally\b',
        ]
        
        # Intent indicators
        self.intent_indicators = {
            "metadata": [
                r'how many', r'count', r'list', r'what.*files', 
                r'what.*languages', r'project.*size'
            ],
            "code": [
                r'how.*work', r'explain', r'analyze', r'show.*code',
                r'implement', r'fix', r'debug', r'review'
            ],
            "structure": [
                r'structure', r'organization', r'where.*located',
                r'find.*file', r'directory'
            ]
        }
    
    def detect_multi_intent(self, query_analysis: QueryAnalysis) -> Tuple[bool, List[str]]:
        """
        Detect if query has multiple intents
        
        Returns:
            (is_multi_intent, [list of intents])
        """
        
        query = query_analysis.normalized_query
        
        # Check if query has conjunction words
        has_conjunction = any(re.search(pattern, query) for pattern in self.conjunction_words)
        
        if not has_conjunction:
            return False, []
        
        # Detect which intents are present
        detected_intents = []
        
        for intent_type, patterns in self.intent_indicators.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    if intent_type not in detected_intents:
                        detected_intents.append(intent_type)
                    break
        
        # Multi-intent if we found more than one
        is_multi = len(detected_intents) > 1
        
        if is_multi:
            console.print(f"[yellow]⚠ Multi-intent query detected: {detected_intents}[/]")
        
        return is_multi, detected_intents
    
    def split_query(self, query: str) -> List[str]:
        """Split multi-intent query into sub-queries"""
        
        # Try to split by conjunction words
        for conjunction_pattern in self.conjunction_words:
            if re.search(conjunction_pattern, query):
                parts = re.split(conjunction_pattern, query, maxsplit=1)
                if len(parts) == 2:
                    return [parts[0].strip(), parts[1].strip()]
        
        # Can't split, return as-is
        return [query]
    
    def create_routing_decision(self, intents: List[str], query_analysis: QueryAnalysis) -> Dict[str, Any]:
        """Create routing decision for multi-intent query"""
        
        needs_metadata = "metadata" in intents or "structure" in intents
        needs_code = "code" in intents or len(query_analysis.file_references) > 0
        
        # Multi-intent queries need both metadata and code
        decision = {
            "strategy": "multi_intent",
            "sub_strategies": intents,
            "needs_code": needs_code,
            "needs_metadata": needs_metadata,
            "can_compute_directly": False,  # Need LLM to combine results
            "confidence": 0.8,
            "reasoning": f"Multi-intent query combining: {', '.join(intents)}"
        }
        
        console.print(f"[green]✓ Multi-intent routing:[/] {intents}")
        
        return decision
    
    def handle_multi_intent_query(self, query_analysis: QueryAnalysis, 
                                  intents: List[str]) -> Dict[str, Any]:
        """
        Handle multi-intent query by combining different data sources
        
        Steps:
        1. Get metadata if needed
        2. Get code chunks if needed
        3. Combine both for LLM
        """
        
        console.print(f"[cyan]→ Handling multi-intent query: {intents}[/]")
        
        result = {
            "metadata_info": None,
            "code_context": None,
            "combined_context": ""
        }
        
        # Get metadata if needed
        if "metadata" in intents or "structure" in intents:
            stats = self.indexer.get_stats()
            languages = set(f.language for f in self.indexer.file_tree if f.language)
            file_list = [f.name for f in self.indexer.file_tree[:20]]
            
            metadata_context = f"""Repository Metadata:
- Total Files: {stats['total_files']}
- Code Files: {stats['code_files']}
- Languages: {', '.join(sorted(languages))}
- Sample Files: {', '.join(file_list)}
{f"  ... and {stats['total_files'] - 20} more files" if stats['total_files'] > 20 else ""}
"""
            
            result["metadata_info"] = metadata_context
            result["combined_context"] += metadata_context + "\n\n"
            
            console.print(f"[green]✓ Added metadata context[/]")
        
        # Code context will be added by the retrieval step
        # This metadata will be prepended to the code context
        
        return result


class QueryDecomposer:
    """
    Decomposes complex queries into simpler sub-queries
    Example: "How many files and how are they connected?" 
    → ["How many files?", "How are files connected?"]
    """
    
    def __init__(self):
        self.conjunction_patterns = [
            r'\band\s+',
            r'\balso\s+',
            r'\bthen\s+',
        ]
    
    def decompose(self, query: str) -> List[str]:
        """Decompose query into sub-queries"""
        
        # Split by conjunctions
        sub_queries = [query]
        
        for pattern in self.conjunction_patterns:
            new_queries = []
            for q in sub_queries:
                parts = re.split(pattern, q, maxsplit=1)
                if len(parts) > 1:
                    # Clean up the parts
                    q1 = parts[0].strip()
                    q2 = parts[1].strip()
                    
                    # Add question mark if missing
                    if q1 and not q1.endswith('?'):
                        q1 += '?'
                    if q2 and not q2.endswith('?'):
                        q2 += '?'
                    
                    new_queries.extend([q1, q2])
                else:
                    new_queries.append(q)
            
            sub_queries = new_queries
        
        # Filter out empty queries
        sub_queries = [q for q in sub_queries if q and len(q) > 3]
        
        if len(sub_queries) > 1:
            console.print(f"[yellow]→ Decomposed into {len(sub_queries)} sub-queries:[/]")
            for i, sq in enumerate(sub_queries, 1):
                console.print(f"  {i}. {sq}")
        
        return sub_queries

