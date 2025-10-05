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
    
    # Small model defaults for local PC
    p.add_argument("--model", default=os.getenv("MODEL_NAME", "microsoft/DialoGPT-small"))
    p.add_argument("--embed-model", default=os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    
    # Reduced parameters for small models
    p.add_argument("--max-chunk-chars", type=int, default=800)
    p.add_argument("--chunk-overlap", type=int, default=100)
    p.add_argument("--max-model-len", type=int, default=1024)
    p.add_argument("--device", default="cpu", help="Force CPU usage for small models")
    p.add_argument("--disable-apply", action="store_true", help="Disable /apply for safety")
    
    # Multi‑agent extras (disabled by default for small models)
    p.add_argument("--planner-model", default=os.getenv("PLANNER_MODEL", None), help="Model to use for planning (defaults to main model if unset)")
    p.add_argument("--judge-model", default=os.getenv("JUDGE_MODEL", None), help="Model to use for validation (defaults to main model if unset)")
    p.add_argument("--num-samples", type=int, default=1, help="How many candidate patches to sample per loop")
    p.add_argument("--max-loops", type=int, default=1, help="Max plan→code→judge loops before returning best so far")
    
    # Small model specific options
    p.add_argument("--use-small-models", action="store_true", default=True, help="Use small models optimized for local PC")
    p.add_argument("--quantize", action="store_true", help="Use quantized models for even smaller memory footprint")
    
    # ShibuDB persistent indexing options
    p.add_argument("--use-persistent-index", action="store_true", default=True, help="Use ShibuDB for persistent indexing")
    p.add_argument("--shibudb-host", default="localhost", help="ShibuDB server host")
    p.add_argument("--shibudb-port", type=int, default=4444, help="ShibuDB server port")
    p.add_argument("--force-rebuild", action="store_true", help="Force rebuild of the entire index")
    
    return p.parse_args()


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
