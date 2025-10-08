"""
Model Selector - Selects the best model for each query
"""

from typing import Dict, List, Optional
from rich.console import Console

from .types import QueryAnalysis, ModelConfig, IntentType, ComplexityLevel

console = Console()


class ModelSelector:
    """
    Selects the best model based on:
    1. Query intent
    2. Complexity
    3. Model capabilities
    4. Performance requirements
    """
    
    def __init__(self, models: Dict[str, ModelConfig]):
        self.models = models
        self.selection_cache: Dict[str, str] = {}
        
        console.print(f"[blue]ModelSelector initialized with {len(models)} models[/]")
    
    def select_model(self, query_analysis: QueryAnalysis) -> ModelConfig:
        """Select the best model for a query"""
        console.print(f"[cyan]Selecting model for intent={query_analysis.intent.value}, complexity={query_analysis.complexity.value}...[/]")
        
        # Score each model
        scores = {}
        for model_name, model_config in self.models.items():
            score = self._score_model(model_config, query_analysis)
            scores[model_name] = score
        
        # Select highest scoring model
        best_model_name = max(scores, key=scores.get)
        best_model = self.models[best_model_name]
        
        console.print(f"[green]Selected model:[/] {best_model.name} (score: {scores[best_model_name]:.2f})")
        return best_model
    
    def _score_model(self, model: ModelConfig, query_analysis: QueryAnalysis) -> float:
        """Score a model for a given query"""
        score = 0.0
        
        # Check capabilities match
        intent_capability_map = {
            IntentType.ANALYSIS: "code_analysis",
            IntentType.DEBUG: "debugging",
            IntentType.CHANGES: "code_generation",
            IntentType.REVIEW: "code_review",
            IntentType.SEARCH: "code_search",
            IntentType.GENERAL: "general_qa"
        }
        
        required_capability = intent_capability_map.get(query_analysis.intent)
        if required_capability and required_capability in model.capabilities:
            score += 10.0
        
        # Check if it's a code model for code-related tasks
        if query_analysis.intent in [IntentType.ANALYSIS, IntentType.DEBUG, IntentType.CHANGES, IntentType.REVIEW]:
            if model.type in ["code", "large"]:
                score += 5.0
        
        # Complexity matching
        if query_analysis.complexity == ComplexityLevel.COMPLEX:
            if model.type == "large" or model.max_tokens >= 4096:
                score += 5.0
        elif query_analysis.complexity == ComplexityLevel.SIMPLE:
            if model.type == "small":
                score += 3.0  # Prefer small models for simple tasks
        
        # File references bonus
        if query_analysis.file_references and "code" in model.type:
            score += 2.0
        
        # Base preference for larger context windows
        score += (model.max_tokens / 1000) * 0.1
        
        return score
    
    def get_model_by_name(self, name: str) -> Optional[ModelConfig]:
        """Get a specific model by name"""
        return self.models.get(name)
    
    def list_models(self) -> List[str]:
        """List all available models"""
        return list(self.models.keys())

