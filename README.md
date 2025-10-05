# RepoCoder API

A FastAPI server that loads a local code LLM and indexes a codebase folder into a ShibuDB vector database for code-aware chunking and retrieval. Serves an HTTP API to answer repo questions and propose patch diffs.

## Features

- **Local LLM Integration**: Uses DeepSeek-Coder-V2-Lite-Instruct by default
- **Persistent Indexing**: ShibuDB vector database for incremental updates (no re-indexing on restart!)
- **Code-Aware Indexing**: ShibuDB vector search with intelligent code chunking (replaces FAISS)
- **Multi-Agent Pipeline**: Optional planner → coder → judge workflow
- **RESTful API**: Clean endpoints for querying and applying changes

## Project Structure

```
repocoder/
├── app.py                    # Main FastAPI application
├── config.py                 # Configuration and CLI parsing
├── models.py                 # Pydantic request/response models
├── indexer.py                # Repository indexing and retrieval
├── persistent_indexer.py     # ShibuDB persistent indexing
├── llm.py                    # Local LLM wrapper
├── prompts.py                # Prompt templates
├── utils.py                  # Utility functions
├── requirements.txt          # Python dependencies
├── SHIBUDB_SETUP.md         # ShibuDB setup guide
└── README.md                # This file
```

## Installation

### Prerequisites

1. **Install ShibuDB** (recommended for persistent indexing):
   - Download from [https://shibudb.org/](https://shibudb.org/)
   - See [SHIBUDB_SETUP.md](SHIBUDB_SETUP.md) for detailed setup instructions
   - Start server: `sudo shibudb start 4444`

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### With Persistent Indexing (Recommended)

```bash
# Start ShibuDB server
sudo shibudb start 4444

# Start RepoCoder with persistent indexing
python app.py --repo /path/to/your/repo --use-persistent-index
```

**Benefits**:
- ⚡ **Fast startup**: Only indexes changed files
- 💾 **Persistent storage**: No re-indexing on restart
- 🔄 **Incremental updates**: Only processes what's new/modified

### Without Persistent Indexing (Legacy)

```bash
python app.py --repo /path/to/your/repo --no-use-persistent-index
```

### Basic Setup

```bash
export MODEL_NAME="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
export EMBED_MODEL="jinaai/jina-embeddings-v2-base-code"
python app.py --repo /path/to/your/repo --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Single-Agent Query
```bash
curl -X POST 'http://localhost:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Add input validation to /api/upload and write unit tests.", "top_k": 12}'
```

#### Multi-Agent Query
```bash
curl -X POST 'http://localhost:8000/query_plus' \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Refactor X with tests", "top_k": 24, "temperature": 0.0}'
```

#### Apply Changes
```bash
curl -X POST 'http://localhost:8000/apply' \
  -H 'Content-Type: application/json' \
  -d '{"diff":"--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,4 @@\n def func():\n+    # Added comment\n     pass"}'
```

## Configuration

### Command Line Options

- `--repo`: Path to the repository to index (required)
- `--host`: Host to bind to (default: 127.0.0.1)
- `--port`: Port to bind to (default: 8000)
- `--model`: LLM model name (default: deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct)
- `--embed-model`: Embedding model name (default: jinaai/jina-embeddings-v2-base-code)
- `--max-chunk-chars`: Maximum characters per chunk (default: 1600)
- `--chunk-overlap`: Overlap between chunks (default: 200)
- `--max-model-len`: Maximum model context length (default: 32768)
- `--device`: Device to use (default: cuda if available, else cpu)
- `--disable-apply`: Disable the /apply endpoint for safety
- `--planner-model`: Model for planning (defaults to main model)
- `--judge-model`: Model for validation (defaults to main model)
- `--num-samples`: Number of candidate patches per loop (default: 2)
- `--max-loops`: Maximum plan→code→judge loops (default: 2)

### Environment Variables

- `MODEL_NAME`: Default LLM model
- `EMBED_MODEL`: Default embedding model
- `PLANNER_MODEL`: Model for planning
- `JUDGE_MODEL`: Model for validation

## GPU Requirements

- PyTorch with CUDA support
- 40+ GB VRAM recommended for optimal performance
- Set `HF_HUB_DISABLE_TELEMETRY=1` and `TRANSFORMERS_OFFLINE=1` for offline usage

## Architecture

### Modules

- **config.py**: Handles CLI arguments and configuration constants
- **models.py**: Pydantic models for API requests/responses
- **indexer.py**: Repository indexing with FAISS vector store
- **llm.py**: Local LLM wrapper with chat formatting
- **prompts.py**: All prompt templates for different agents
- **utils.py**: Utility functions for context formatting and diff application
- **app.py**: Main FastAPI application with all endpoints

### Multi-Agent Pipeline

The `/query_plus` endpoint implements a sophisticated multi-agent workflow:

1. **Planner**: Analyzes the request and creates a detailed task specification
2. **Coder**: Generates multiple candidate patches based on the specification
3. **Judge**: Evaluates each candidate and scores them
4. **Iteration**: Repeats the process with refined queries until high confidence is achieved

This modular architecture makes the codebase maintainable, testable, and extensible.
