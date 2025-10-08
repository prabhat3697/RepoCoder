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
    # Python
    ".py", ".pyi", ".pyw", ".pyx", ".pxd", ".pyd", ".ipynb",
    
    # JavaScript/TypeScript
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".d.ts",
    
    # Web - HTML/CSS/Templates
    ".html", ".htm", ".xhtml", ".xml", ".svg",
    ".css", ".scss", ".sass", ".less", ".styl", ".stylus",
    ".vue", ".svelte", ".astro", ".ejs", ".pug", ".jade", ".hbs", ".handlebars",
    ".njk", ".nunjucks", ".twig", ".mustache", ".liquid",
    ".jsp", ".jspx", ".asp", ".aspx", ".cshtml", ".vbhtml", ".razor",
    
    # Java/JVM Languages
    ".java", ".kt", ".kts", ".groovy", ".gradle", ".scala", ".clj", ".cljs", ".cljc",
    
    # C/C++
    ".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".h++",
    ".cu", ".cuh", ".cuda",
    
    # C#/.NET
    ".cs", ".csx", ".fs", ".fsx", ".fsi", ".vb",
    
    # Go
    ".go", ".mod", ".sum",
    
    # Rust
    ".rs", ".rlib",
    
    # Swift/Objective-C
    ".swift", ".m", ".mm", ".h",
    
    # PHP
    ".php", ".php3", ".php4", ".php5", ".php7", ".phtml",
    
    # Ruby
    ".rb", ".rake", ".gemspec", ".ru", ".erb",
    
    # Perl
    ".pl", ".pm", ".t", ".pod",
    
    # Shell Scripts
    ".sh", ".bash", ".zsh", ".fish", ".ksh", ".csh", ".tcsh",
    
    # PowerShell
    ".ps1", ".psm1", ".psd1",
    
    # Batch/CMD
    ".bat", ".cmd",
    
    # R
    ".r", ".R", ".rmd", ".Rmd",
    
    # Lua
    ".lua",
    
    # Dart/Flutter
    ".dart",
    
    # Elixir
    ".ex", ".exs",
    
    # Erlang
    ".erl", ".hrl",
    
    # Haskell
    ".hs", ".lhs",
    
    # OCaml/F#
    ".ml", ".mli", ".mll", ".mly",
    
    # Lisp/Scheme
    ".lisp", ".lsp", ".scm", ".ss",
    
    # Julia
    ".jl",
    
    # Nim
    ".nim", ".nims",
    
    # Crystal
    ".cr",
    
    # Zig
    ".zig",
    
    # V
    ".v", ".vv",
    
    # Assembly
    ".asm", ".s", ".S",
    
    # SQL/Database
    ".sql", ".psql", ".plsql", ".tsql", ".mysql", ".pgsql",
    
    # Config Files
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".config",
    ".json", ".json5", ".jsonc", ".json.tmpl",
    ".xml", ".plist", ".properties", ".env", ".env.example", ".env.local",
    ".env.development", ".env.production", ".env.test", ".env.staging",
    ".editorconfig", ".prettierrc", ".eslintrc", ".babelrc",
    
    # Documentation
    ".md", ".markdown", ".rst", ".txt", ".adoc", ".asciidoc", ".textile",
    ".org", ".rdoc", ".pod", ".man",
    
    # Build/Project Files
    ".gradle", ".maven", ".sbt", ".mill", ".bazel", ".buck",
    ".cmake", ".make", ".mk", ".ninja",
    
    # Docker/Container
    ".dockerfile", ".containerfile",
    
    # Terraform/IaC
    ".tf", ".tfvars", ".hcl",
    
    # GraphQL
    ".graphql", ".gql",
    
    # Protocol Buffers
    ".proto", ".protobuf",
    
    # Thrift
    ".thrift",
    
    # WASM
    ".wasm", ".wat",
    
    # Vim
    ".vim", ".vimrc",
    
    # Emacs
    ".el", ".elc",
    
    # Jupyter
    ".ipynb",
    
    # LaTeX
    ".tex", ".latex", ".ltx",
    
    # Solidity/Smart Contracts
    ".sol",
    
    # Vyper
    ".vy",
    
    # MATLAB
    ".m", ".mat",
    
    # Mathematica
    ".nb", ".wl",
    
    # Fortran
    ".f", ".for", ".f90", ".f95", ".f03",
    
    # COBOL
    ".cob", ".cbl",
    
    # Ada
    ".ada", ".adb", ".ads",
    
    # D
    ".d", ".di",
    
    # Prolog
    ".pl", ".pro", ".P",
    
    # Smalltalk
    ".st",
    
    # Tcl
    ".tcl",
    
    # Verilog/VHDL
    ".v", ".vh", ".sv", ".vhd", ".vhdl",
    
    # Makefile variants
    ".makefile", ".gnumakefile",
    
    # Git
    ".gitignore", ".gitattributes", ".gitmodules",
    
    # CI/CD
    ".gitlab-ci.yml", ".travis.yml", ".circleci", ".jenkinsfile",
    
    # Package managers
    ".package.json", ".package-lock.json", ".yarn.lock", ".pnpm-lock.yaml",
    ".cargo.toml", ".cargo.lock", ".gemfile.lock", ".pipfile.lock",
    ".poetry.lock", ".composer.json", ".composer.lock",
    
    # App-specific
    ".xcconfig", ".pbxproj", ".storyboard", ".xib",
    ".gradle.kts", ".build.gradle",
}

IGNORE_DIRS = {
    # Version Control
    ".git", ".hg", ".svn", ".bzr", ".fossil",
    
    # Dependencies
    "node_modules", "bower_components", "jspm_packages",
    "vendor", "packages", "lib-cov",
    
    # Python
    "venv", ".venv", "env", ".env", "ENV", "virtualenv",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".tox",
    "*.egg-info", ".eggs", ".Python", "pip-log.txt",
    
    # Build/Dist
    "dist", "build", "out", "target", "bin", "obj",
    ".next", ".nuxt", ".cache", ".parcel-cache",
    ".output", ".vercel", ".netlify",
    
    # IDE/Editor
    ".idea", ".vscode", ".vs", ".eclipse", ".project",
    ".settings", ".classpath", ".factorypath",
    "*.swp", "*.swo", "*~",
    
    # OS
    ".DS_Store", "Thumbs.db", "desktop.ini",
    
    # Coverage/Test
    "coverage", ".coverage", ".nyc_output", "htmlcov",
    ".pytest_cache", ".rspec",
    
    # Logs
    "logs", "*.log", "npm-debug.log*", "yarn-debug.log*",
    "yarn-error.log*", "lerna-debug.log*",
    
    # Temporary
    "tmp", "temp", ".tmp", ".temp",
    
    # Documentation builds
    "_build", ".docusaurus", ".jekyll-cache",
    "site", "public",
}
