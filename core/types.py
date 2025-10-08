"""
Core data types for RepoCoder V2
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class IntentType(Enum):
    """Types of user intents"""
    ANALYSIS = "analysis"              # Explain/understand code
    DEBUG = "debug"                    # Fix bugs/troubleshoot
    CHANGES = "changes"                # Add/modify/refactor
    REVIEW = "review"                  # Check/validate code
    SEARCH = "search"                  # Find/locate code
    GENERAL = "general"                # General questions
    

class ComplexityLevel(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class FileNode:
    """Represents a file in the file tree"""
    path: str
    name: str
    extension: str
    size: int
    language: Optional[str] = None
    is_code: bool = True
    

@dataclass
class CodeChunk:
    """Represents a chunk of code"""
    id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    language: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class FileReference:
    """Represents a file reference detected in query"""
    filename: str
    full_path: Optional[str] = None
    confidence: float = 0.0
    line_number: Optional[int] = None
    context: str = ""
    

@dataclass
class QueryAnalysis:
    """Analysis of user query"""
    original_query: str
    normalized_query: str
    intent: IntentType
    complexity: ComplexityLevel
    file_references: List[FileReference] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class RetrievalContext:
    """Context retrieved for query"""
    chunks: List[CodeChunk]
    file_tree: List[FileNode]
    total_chunks: int
    strategy_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
    """Configuration for a model"""
    name: str
    type: str  # "code", "general", "small", "large"
    capabilities: List[str]
    max_tokens: int
    temperature: float = 0.2
    device: str = "auto"
    

@dataclass
class Response:
    """Final response to user"""
    analysis: str
    plan: str = ""
    changes: List[Dict[str, Any]] = field(default_factory=list)
    model_used: str = ""
    took_ms: int = 0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

