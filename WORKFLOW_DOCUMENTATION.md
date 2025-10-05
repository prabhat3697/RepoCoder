# RepoCoder Workflow Documentation

## Overview
RepoCoder is a FastAPI-based system that uses local LLMs to analyze code repositories and provide intelligent code suggestions, security analysis, and automated fixes.

## Complete Step-by-Step Workflow

### Phase 1: System Initialization

#### 1.1 Command Line Parsing
- **File**: `config.py`
- **Process**:
  - Parse command line arguments (--repo, --model, --embed-model, etc.)
  - Set default values for small models (DialoGPT-small, all-MiniLM-L6-v2)
  - Configure device settings (CPU for small models)
  - Set model parameters (max_model_len=1024, max_chunk_chars=800)

#### 1.2 Model Loading
- **File**: `llm.py`
- **Process**:
  - Load tokenizer for the specified model
  - Load the language model (with CPU optimization for small models)
  - Configure quantization if requested (8-bit for memory efficiency)
  - Set up device mapping (CPU/GPU)
  - Initialize embedding model for vector search

#### 1.3 Repository Indexing
- **File**: `indexer.py`
- **Process**:
  - Scan repository directory recursively
  - Filter files by extension (CODE_EXTS: .py, .js, .ts, .java, etc.)
  - Skip ignored directories (IGNORE_DIRS: .git, node_modules, etc.)
  - Read file contents with UTF-8 encoding
  - Chunk files into manageable pieces (default: 800 chars with 100 char overlap)
  - Generate embeddings for each chunk using sentence-transformers
  - Build FAISS vector index for fast similarity search
  - Store metadata mapping (chunk_id → file_path, start, end)

### Phase 2: API Server Setup

#### 2.1 FastAPI Application Creation
- **File**: `app.py`
- **Process**:
  - Create FastAPI app instance
  - Add CORS middleware for cross-origin requests
  - Initialize all three LLM instances (coder, planner, judge)
  - Set up route handlers for different endpoints

#### 2.2 Endpoint Registration
- **Endpoints Created**:
  - `GET /health` - Health check
  - `POST /index` - Re-index repository
  - `POST /query` - Single-agent code analysis
  - `POST /query_plus` - Multi-agent analysis pipeline
  - `POST /apply` - Apply generated patches

### Phase 3: Query Processing (Single Agent - /query)

#### 3.1 Request Reception
- **Input**: JSON with prompt, top_k, max_new_tokens, temperature
- **Validation**: Pydantic model validation
- **Start**: Timer for performance measurement

#### 3.2 Context Retrieval
- **Process**:
  - Use embedding model to encode user query
  - Search FAISS index for top-k most similar code chunks
  - Retrieve actual code chunks with metadata
  - Format context with file paths and line numbers

#### 3.3 Prompt Construction
- **Small Models (≤1024 tokens)**:
  - Use SIMPLE_SYSTEM_TEMPLATE (security expert role)
  - Use SIMPLE_USER_TEMPLATE (task + limited context)
  - Limit context to 2000 characters
- **Large Models (>1024 tokens)**:
  - Use full SYSTEM_TEMPLATE (senior engineer role)
  - Use full USER_TEMPLATE (detailed context)
  - Include all retrieved chunks

#### 3.4 LLM Generation
- **Process**:
  - Calculate safe token limits (max_model_len // 2)
  - Format prompt for model type (GPT-2 vs ChatML)
  - Generate response with specified parameters
  - Handle generation errors gracefully

#### 3.5 Response Processing
- **JSON Parsing**:
  - Try to parse as JSON first
  - If fails, use parse_simple_response() for small models
  - Extract analysis, plan, and changes
- **Fallback**: Wrap raw response as analysis-only

#### 3.6 Response Formatting
- **Output**: QueryResponse with model, timing, retrieved chunks, and structured result

### Phase 4: Multi-Agent Processing (/query_plus)

#### 4.1 Initial Planning
- **Planner Agent**:
  - Retrieve base context chunks
  - Use PLANNER_SYSTEM prompt (tech lead role)
  - Generate task specification with goals, constraints, acceptance criteria
  - Parse JSON specification

#### 4.2 Iterative Refinement Loop
- **For each iteration (max_loops)**:
  
  **4.2.1 Refined Retrieval**:
  - Combine original prompt with planner signals
  - Retrieve more targeted code chunks
  - Build focused context
  
  **4.2.2 Candidate Generation**:
  - Generate multiple candidate solutions (num_samples)
  - Use coder agent with full system template
  - Parse each candidate as JSON
  
  **4.2.3 Candidate Evaluation**:
  - Use judge agent to score each candidate
  - Apply JUDGE_SYSTEM prompt (code reviewer role)
  - Score on correctness, minimality, style compliance
  - Parse verdict JSON (score, verdict, reasons, risks)
  
  **4.2.4 Best Selection**:
  - Sort candidates by score
  - Update best candidate if score improves
  - Early termination if score ≥ 85

#### 4.3 Final Response
- **Output**: Enhanced QueryResponse with planner spec and judge evaluation

### Phase 5: Patch Application (/apply)

#### 5.1 Diff Processing
- **Input**: Unified diff text
- **Process**:
  - Write diff to temporary file
  - Use system `patch` command to apply changes
  - Parse patch output for changed files
  - Clean up temporary files

#### 5.2 Error Handling
- **Validation**: Check patch command return code
- **Error Response**: Return detailed error messages
- **Safety**: Only enabled if --disable-apply not set

## Data Flow Diagram

```
User Query → Embedding → FAISS Search → Context Retrieval
     ↓
Prompt Construction → LLM Generation → Response Parsing
     ↓
Structured Output → JSON Response → User
```

## Key Components

### 1. Repository Indexer (`indexer.py`)
- **Purpose**: Convert codebase into searchable vector database
- **Key Features**:
  - Code-aware chunking with overlap
  - FAISS vector index for fast similarity search
  - Metadata preservation (file paths, line numbers)

### 2. Local LLM Wrapper (`llm.py`)
- **Purpose**: Interface with local language models
- **Key Features**:
  - CPU/GPU optimization
  - Quantization support
  - Prompt formatting for different model types
  - Error handling and fallbacks

### 3. Prompt Templates (`prompts.py`)
- **Purpose**: Standardized prompts for different agents
- **Templates**:
  - SYSTEM_TEMPLATE: Senior engineer role
  - SIMPLE_SYSTEM_TEMPLATE: Security expert role
  - PLANNER_SYSTEM: Tech lead role
  - JUDGE_SYSTEM: Code reviewer role

### 4. Utility Functions (`utils.py`)
- **Purpose**: Helper functions for context formatting and patch application
- **Functions**:
  - make_context(): Format retrieved chunks
  - apply_unified_diff(): Apply patches safely

## Performance Characteristics

### Memory Usage
- **Small Models**: ~1-3GB RAM
- **Large Models**: ~10-40GB RAM
- **Quantization**: 50% memory reduction

### Response Times
- **Simple Queries**: 5-15 seconds
- **Code Analysis**: 10-30 seconds
- **Multi-Agent**: 30-60 seconds

### Scalability
- **Repository Size**: Limited by available RAM
- **Concurrent Requests**: Single-threaded (can be scaled with multiple instances)
- **Index Size**: Grows linearly with codebase size

## Security Considerations

### Input Validation
- **File Paths**: Validated against repository root
- **Patch Application**: Uses system patch command with validation
- **Context Limits**: Prevents prompt injection attacks

### Safety Features
- **Apply Endpoint**: Can be disabled with --disable-apply
- **Error Handling**: Graceful degradation on failures
- **Resource Limits**: Token and context length limits

## Configuration Options

### Model Selection
- **Small Models**: distilgpt2, gpt2, microsoft/DialoGPT-small
- **Code Models**: microsoft/CodeGPT-small-py, Salesforce/codegen-350M-mono
- **Embedding Models**: all-MiniLM-L6-v2, all-MiniLM-L12-v2

### Performance Tuning
- **Chunk Size**: Adjust max_chunk_chars for memory/quality tradeoff
- **Context Length**: Adjust max_model_len for model capacity
- **Retrieval**: Adjust top_k for context relevance
- **Generation**: Adjust max_new_tokens for response length

This workflow enables RepoCoder to provide intelligent code analysis and suggestions while running entirely on local hardware with small, efficient models.
