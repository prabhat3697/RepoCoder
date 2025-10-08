"""
Query Analyzer - Understands user queries
Can use LLM for complex analysis
"""

import re
from typing import List, Optional
from rich.console import Console

from .types import QueryAnalysis, FileReference, IntentType, ComplexityLevel

console = Console()


class QueryAnalyzer:
    """
    Analyzes user queries to understand:
    1. What files they're referring to
    2. What intent they have (analyze, debug, change, etc.)
    3. What entities they mention (functions, classes, etc.)
    """
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for query understanding"""
        
        # File reference patterns
        self.file_patterns = [
            r'\b(\w+\.\w{2,4})\b',  # filename.ext
            r'["\']([^"\']+\.\w{2,4})["\']',  # "filename.ext"
            r'\b([a-zA-Z0-9_\-/]+\.\w{2,4})\b',  # path/filename.ext
        ]
        
        # Intent patterns
        self.intent_patterns = {
            IntentType.ANALYSIS: [
                r'\bhow\s+(does|is|do)\b',
                r'\bexplain\b',
                r'\bwhat\s+(is|does|do)\b',
                r'\bunderstand\b',
                r'\banalyze\b',
                r'\bdescribe\b',
                r'\bshow\s+me\b',
            ],
            IntentType.DEBUG: [
                r'\bfix\b',
                r'\bbug\b',
                r'\berror\b',
                r'\bissue\b',
                r'\bproblem\b',
                r'\bwhy\s+.*(not\s+working|failing|broken)\b',
                r'\btroubleshoot\b',
                r'\bdebug\b',
            ],
            IntentType.CHANGES: [
                r'\badd\b',
                r'\bcreate\b',
                r'\bimplement\b',
                r'\bmodify\b',
                r'\bchange\b',
                r'\brefactor\b',
                r'\bupdate\b',
                r'\bwrite\b',
                r'\bbuild\b',
            ],
            IntentType.REVIEW: [
                r'\breview\b',
                r'\bcheck\b',
                r'\bvalidate\b',
                r'\bimprove\b',
                r'\boptimize\b',
                r'\bassess\b',
            ],
            IntentType.SEARCH: [
                r'\bfind\b',
                r'\bsearch\b',
                r'\blocate\b',
                r'\bwhere\s+is\b',
                r'\bshow\s+all\b',
                r'\blist\b',
            ],
        }
        
        # Complexity indicators
        self.complexity_patterns = {
            ComplexityLevel.SIMPLE: [
                r'\bhow\s+many\b',
                r'\bcount\b',
                r'\blist\b',
                r'\bshow\b',
                r'\bfind\b',
            ],
            ComplexityLevel.COMPLEX: [
                r'\barchitecture\b',
                r'\bsystem\b',
                r'\bframework\b',
                r'\brefactor\b',
                r'\bredesign\b',
                r'\bmultiple\b.*\bfiles\b',
            ],
        }
    
    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze a user query"""
        console.print(f"[cyan]Analyzing query:[/] {query}")
        
        # Normalize query
        normalized_query = query.lower().strip()
        
        # Detect file references
        file_refs = self._detect_files(query)
        
        # Detect intent
        intent = self._detect_intent(normalized_query)
        
        # Detect complexity
        complexity = self._detect_complexity(normalized_query)
        
        # Extract entities (simple version, can use LLM later)
        entities = self._extract_entities(normalized_query)
        
        # Calculate confidence
        confidence = self._calculate_confidence(file_refs, intent, entities)
        
        analysis = QueryAnalysis(
            original_query=query,
            normalized_query=normalized_query,
            intent=intent,
            complexity=complexity,
            file_references=file_refs,
            entities=entities,
            confidence=confidence,
            metadata={
                "has_file_references": len(file_refs) > 0,
                "entity_count": len(entities)
            }
        )
        
        console.print(f"[green]Query analysis complete:[/] intent={intent.value}, complexity={complexity.value}")
        return analysis
    
    def _detect_files(self, query: str) -> List[FileReference]:
        """Detect file references in query"""
        files = []
        query_lower = query.lower()
        
        for pattern in self.file_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                filename = match.group(1)
                
                # Skip common false positives
                if filename in ['e.g', 'i.e', 'etc']:
                    continue
                
                # Check if it looks like a real file
                if '.' in filename and len(filename) > 3:
                    files.append(FileReference(
                        filename=filename,
                        confidence=0.8,
                        context=match.group(0)
                    ))
        
        # Remove duplicates
        unique_files = {}
        for file_ref in files:
            key = file_ref.filename.lower()
            if key not in unique_files or file_ref.confidence > unique_files[key].confidence:
                unique_files[key] = file_ref
        
        return list(unique_files.values())
    
    def _detect_intent(self, query: str) -> IntentType:
        """Detect user intent"""
        scores = {intent: 0 for intent in IntentType}
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    scores[intent] += 1
        
        # Find highest scoring intent
        max_score = max(scores.values())
        if max_score > 0:
            for intent, score in scores.items():
                if score == max_score:
                    return intent
        
        # Default to ANALYSIS
        return IntentType.ANALYSIS
    
    def _detect_complexity(self, query: str) -> ComplexityLevel:
        """Detect query complexity"""
        for level, patterns in self.complexity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return level
        
        # Default to MEDIUM
        return ComplexityLevel.MEDIUM
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities (functions, classes, variables) from query"""
        # Simple regex-based extraction
        # Can be enhanced with LLM later
        
        entities = []
        
        # Extract quoted terms
        quoted = re.findall(r'["\']([^"\']+)["\']', query)
        entities.extend(quoted)
        
        # Extract CamelCase or snake_case identifiers
        identifiers = re.findall(r'\b([A-Z][a-zA-Z0-9]*|[a-z_][a-z0-9_]+)\b', query)
        entities.extend(identifiers)
        
        # Remove duplicates and common words
        stop_words = {'the', 'is', 'are', 'how', 'what', 'why', 'when', 'where', 'my', 'your', 'this', 'that'}
        entities = list(set(e for e in entities if e.lower() not in stop_words))
        
        return entities[:10]  # Limit to top 10
    
    def _calculate_confidence(self, files: List[FileReference], intent: IntentType, 
                             entities: List[str]) -> float:
        """Calculate overall confidence in query analysis"""
        confidence = 0.5  # Base confidence
        
        # Boost if files are detected
        if files:
            confidence += 0.2 * min(len(files), 3) / 3
        
        # Boost if entities are detected
        if entities:
            confidence += 0.1 * min(len(entities), 5) / 5
        
        # Boost if intent is clear (not general)
        if intent != IntentType.GENERAL:
            confidence += 0.2
        
        return min(confidence, 1.0)

