#!/usr/bin/env python3
"""
Configuration and CLI argument parsing for RepoCoder API.
"""

import argparse
import os
import torch


def parse_args():
    """Parse command line arguments."""
    p = argparse.ArgumentParser(description="RepoCoder API")
    p.add_argument("--repo", required=True, help="Path to the repo/code folder to index")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    
    # Environment-based model selection
    p.add_argument("--environment", choices=["local", "vm"], default="local", 
                   help="Environment type: 'local' for small models, 'vm' for large models")
    
    # Primary models (can specify multiple for routing)
    p.add_argument("--models", nargs="+", 
                   default=os.getenv("MODELS", "microsoft/DialoGPT-small").split(","),
                   help="Comma-separated list of models to load for intelligent routing")
    p.add_argument("--primary-model", default=os.getenv("PRIMARY_MODEL", None),
                   help="Primary model to use (defaults to first in --models)")
    p.add_argument("--embed-model", default=os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    
    # Model configuration
    p.add_argument("--max-chunk-chars", type=int, default=800)
    p.add_argument("--chunk-overlap", type=int, default=100)
    p.add_argument("--max-model-len", type=int, default=1024)
    p.add_argument("--device", default="cpu", help="Device to use (cpu/cuda/auto)")
    p.add_argument("--disable-apply", action="store_true", help="Disable /apply for safety")
    
    # Multi‑agent extras
    p.add_argument("--planner-model", default=os.getenv("PLANNER_MODEL", None), 
                   help="Model to use for planning (defaults to primary model)")
    p.add_argument("--judge-model", default=os.getenv("JUDGE_MODEL", None), 
                   help="Model to use for validation (defaults to primary model)")
    p.add_argument("--num-samples", type=int, default=1, help="How many candidate patches to sample per loop")
    p.add_argument("--max-loops", type=int, default=1, help="Max plan→code→judge loops before returning best so far")
    
    # Model optimization
    p.add_argument("--quantize", action="store_true", help="Use quantized models for smaller memory footprint")
    p.add_argument("--enable-routing", action="store_true", default=True, 
                   help="Enable intelligent query routing between models")
    
    # ShibuDB persistent indexing options
    p.add_argument("--use-persistent-index", action="store_true", default=True, help="Use ShibuDB for persistent indexing")
    p.add_argument("--shibudb-host", default="localhost", help="ShibuDB server host")
    p.add_argument("--shibudb-port", type=int, default=4444, help="ShibuDB server port")
    p.add_argument("--force-rebuild", action="store_true", help="Force rebuild of the entire index")
    
    return p.parse_args()


def get_environment_defaults(environment: str) -> dict:
    """Get default model configurations for different environments."""
    if environment == "local":
        return {
            "models": ["microsoft/DialoGPT-small", "microsoft/CodeGPT-small-py"],
            "primary_model": "microsoft/DialoGPT-small",
            "max_model_len": 1024,
            "device": "cpu",
            "quantize": False,  # Disabled for CPU-only systems
            "max_chunk_chars": 800,
            "chunk_overlap": 100
        }
    else:  # vm
        return {
            "models": [
                "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
                "codellama/CodeLlama-7b-Instruct-hf",
                "microsoft/DialoGPT-large"
            ],
            "primary_model": "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
            "max_model_len": 4096,
            "device": "auto",
            "quantize": False,
            "max_chunk_chars": 1600,
            "chunk_overlap": 200
        }


# Constants
CODE_EXTS = {
    ".py", ".pyi", ".ipynb",
    ".js", ".jsx", ".ts", ".tsx",
    ".java", ".kt", ".go", ".rs", ".cpp", ".cc", ".c", ".h", ".hpp",
    ".cs", ".php", ".rb", ".swift", ".m", ".mm",
    ".sql", ".sh", ".bash", ".zsh", ".ps1", ".yaml", ".yml", ".toml", ".ini",
    ".md", ".json"
}

IGNORE_DIRS = {".git", ".hg", ".svn", "node_modules", "venv", ".venv", "__pycache__", ".mypy_cache"}
