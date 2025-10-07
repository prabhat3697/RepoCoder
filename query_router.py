#!/usr/bin/env python3
"""
Intelligent query routing system for RepoCoder.
Routes queries to appropriate models based on intent and complexity.
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from rich.console import Console

console = Console()


class QueryType(Enum):
    """Types of queries we can handle."""
    CODE_ANALYSIS = "code_analysis"      # "How does this function work?"
    CODE_GENERATION = "code_generation"  # "Add a new feature"
    CODE_REVIEW = "code_review"          # "Review this code"
    DOCUMENTATION = "documentation"      # "What does this do?"
    DEBUGGING = "debugging"              # "Why is this failing?"
    REFACTORING = "refactoring"          # "Refactor this code"
    TESTING = "testing"                  # "Write tests for this"
    GENERAL_INFO = "general_info"        # "How many files are there?"
    SEARCH = "search"                    # "Find all functions that..."
    EXPLANATION = "explanation"          # "Explain this code"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    type: str  # "code", "general", "small", "large"
    max_tokens: int
    temperature: float
    description: str


@dataclass
class QueryIntent:
    """Analyzed query intent."""
    query_type: QueryType
    complexity: str  # "simple", "medium", "complex"
    requires_code_context: bool
    confidence: float
    suggested_model: str
    reasoning: str


class QueryRouter:
    """Routes queries to appropriate models based on intent analysis."""
    
    def __init__(self, model_configs: Dict[str, ModelConfig]):
        self.model_configs = model_configs
        
        # Query patterns for intent detection
        self.patterns = {
            QueryType.CODE_ANALYSIS: [
                r"how does.*work",
                r"explain.*function",
                r"what does.*do",
                r"analyze.*code",
                r"understand.*implementation",
                r"break down.*code"
            ],
            QueryType.CODE_GENERATION: [
                r"add.*feature",
                r"implement.*function",
                r"create.*class",
                r"write.*code",
                r"generate.*function",
                r"build.*component"
            ],
            QueryType.CODE_REVIEW: [
                r"review.*code",
                r"check.*implementation",
                r"validate.*code",
                r"improve.*code",
                r"optimize.*function"
            ],
            QueryType.DEBUGGING: [
                r"why.*error",
                r"debug.*issue",
                r"fix.*bug",
                r"troubleshoot",
                r"error.*occurring",
                r"not working"
            ],
            QueryType.REFACTORING: [
                r"refactor.*code",
                r"restructure.*function",
                r"clean up.*code",
                r"improve.*structure",
                r"reorganize.*code"
            ],
            QueryType.TESTING: [
                r"write.*test",
                r"create.*test",
                r"test.*function",
                r"unit test",
                r"test coverage"
            ],
            QueryType.DOCUMENTATION: [
                r"document.*function",
                r"add.*comment",
                r"explain.*purpose",
                r"describe.*behavior"
            ],
            QueryType.GENERAL_INFO: [
                r"how many.*files",
                r"count.*files",
                r"list.*files",
                r"what.*in.*project",
                r"project.*structure",
                r"repository.*info"
            ],
            QueryType.SEARCH: [
                r"find.*function",
                r"search.*for",
                r"locate.*code",
                r"where.*defined",
                r"show.*all.*functions"
            ],
            QueryType.EXPLANATION: [
                r"explain.*concept",
                r"what.*means",
                r"describe.*algorithm",
                r"how.*works"
            ]
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            "simple": [
                r"count", r"how many", r"list", r"show", r"find", r"where"
            ],
            "medium": [
                r"explain", r"analyze", r"review", r"improve", r"optimize"
            ],
            "complex": [
                r"implement", r"create", r"build", r"refactor", r"design", 
                r"architecture", r"system", r"framework"
            ]
        }
    
    def analyze_query(self, query: str) -> QueryIntent:
        """Analyze query to determine intent and routing."""
        query_lower = query.lower()
        
        # Find matching query type
        matched_type = QueryType.GENERAL_INFO
        max_confidence = 0.0
        reasoning = "Default to general info query"
        
        for query_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    matched_type = query_type
                    max_confidence = 0.8
                    reasoning = f"Matched pattern: {pattern}"
                    break
            if max_confidence > 0:
                break
        
        # Determine complexity
        complexity = "medium"
        for comp_level, indicators in self.complexity_indicators.items():
            for indicator in indicators:
                if re.search(indicator, query_lower):
                    complexity = comp_level
                    break
            if complexity != "medium":
                break
        
        # Check if code context is required
        requires_code_context = matched_type in [
            QueryType.CODE_ANALYSIS, QueryType.CODE_GENERATION, 
            QueryType.CODE_REVIEW, QueryType.DEBUGGING, 
            QueryType.REFACTORING, QueryType.TESTING,
            QueryType.SEARCH, QueryType.EXPLANATION
        ]
        
        # Suggest appropriate model
        suggested_model = self._suggest_model(matched_type, complexity, requires_code_context)
        
        return QueryIntent(
            query_type=matched_type,
            complexity=complexity,
            requires_code_context=requires_code_context,
            confidence=max_confidence,
            suggested_model=suggested_model,
            reasoning=reasoning
        )
    
    def _suggest_model(self, query_type: QueryType, complexity: str, requires_code_context: bool) -> str:
        """Suggest the best model for the query."""
        
        # For code-related queries, prefer code models
        if requires_code_context:
            if complexity == "complex":
                # Prefer large code models for complex tasks
                for name, config in self.model_configs.items():
                    if config.type == "code" and "large" in config.type:
                        return name
                # Fallback to any code model
                for name, config in self.model_configs.items():
                    if config.type == "code":
                        return name
            
            elif complexity == "simple":
                # Can use smaller models for simple code queries
                for name, config in self.model_configs.items():
                    if config.type in ["code", "small"]:
                        return name
        
        # For general queries, use general or small models
        if query_type == QueryType.GENERAL_INFO:
            for name, config in self.model_configs.items():
                if config.type in ["general", "small"]:
                    return name
        
        # Default fallback
        return list(self.model_configs.keys())[0]
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model."""
        return self.model_configs.get(model_name)
    
    def route_query(self, query: str, available_models: List[str]) -> Tuple[str, QueryIntent]:
        """Route query to the best available model."""
        intent = self.analyze_query(query)
        
        # Check if suggested model is available
        if intent.suggested_model in available_models:
            selected_model = intent.suggested_model
        else:
            # Find best alternative
            selected_model = self._find_best_alternative(intent, available_models)
        
        console.print(f"[blue]Query Analysis:[/] {intent.query_type.value} ({intent.complexity})")
        console.print(f"[blue]Reasoning:[/] {intent.reasoning}")
        console.print(f"[blue]Selected Model:[/] {selected_model}")
        
        return selected_model, intent
    
    def _find_best_alternative(self, intent: QueryIntent, available_models: List[str]) -> str:
        """Find the best alternative model from available ones."""
        # Priority order for different query types
        if intent.requires_code_context:
            # Prefer code models, then general models
            for model in available_models:
                config = self.model_configs.get(model)
                if config and config.type == "code":
                    return model
            for model in available_models:
                config = self.model_configs.get(model)
                if config and config.type == "general":
                    return model
        
        # Default to first available
        return available_models[0] if available_models else "default"


def create_default_model_configs() -> Dict[str, ModelConfig]:
    """Create default model configurations for different environments."""
    return {
        # Small models for local development
        "microsoft/DialoGPT-small": ModelConfig(
            name="microsoft/DialoGPT-small",
            type="general",
            max_tokens=256,
            temperature=0.7,
            description="Small general-purpose model for basic queries"
        ),
        "distilbert-base-uncased": ModelConfig(
            name="distilbert-base-uncased", 
            type="small",
            max_tokens=128,
            temperature=0.5,
            description="Very small model for simple tasks"
        ),
        
        # Code models (small to large)
        "microsoft/CodeGPT-small-py": ModelConfig(
            name="microsoft/CodeGPT-small-py",
            type="code",
            max_tokens=512,
            temperature=0.2,
            description="Small code model for Python"
        ),
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct": ModelConfig(
            name="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            type="code",
            max_tokens=2048,
            temperature=0.1,
            description="Medium code model for general programming"
        ),
        "codellama/CodeLlama-7b-Instruct-hf": ModelConfig(
            name="codellama/CodeLlama-7b-Instruct-hf",
            type="code",
            max_tokens=4096,
            temperature=0.1,
            description="Large code model for complex tasks"
        ),
        
        # Large general models for VM
        "microsoft/DialoGPT-large": ModelConfig(
            name="microsoft/DialoGPT-large",
            type="general",
            max_tokens=1024,
            temperature=0.7,
            description="Large general model for complex queries"
        ),
        "gpt2-large": ModelConfig(
            name="gpt2-large",
            type="general",
            max_tokens=1024,
            temperature=0.7,
            description="Large general model"
        )
    }
