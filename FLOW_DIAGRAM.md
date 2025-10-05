# RepoCoder Flow Diagram

## System Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  FastAPI Server │───▶│  Local LLM      │
│   (HTTP POST)   │    │  (app.py)       │    │  (llm.py)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Repository     │
                       │  Indexer        │
                       │  (indexer.py)   │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  FAISS Vector   │
                       │  Database       │
                       └─────────────────┘
```

## Detailed Workflow Flow

### 1. INITIALIZATION PHASE
```
Start Application
        │
        ▼
┌─────────────────┐
│ Parse CLI Args  │
│ (config.py)     │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Load Models     │
│ - LLM Model     │
│ - Embedding     │
│ - Quantization  │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Index Repository│
│ - Scan Files    │
│ - Chunk Code    │
│ - Generate      │
│   Embeddings    │
│ - Build FAISS   │
│   Index         │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Start API Server│
│ - FastAPI App   │
│ - CORS Middleware│
│ - Route Handlers│
└─────────────────┘
```

### 2. SINGLE AGENT QUERY (/query)
```
User Sends Query
        │
        ▼
┌─────────────────┐
│ Validate Request│
│ (Pydantic)      │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Retrieve Context│
│ - Encode Query  │
│ - Search FAISS  │
│ - Get Top-K     │
│   Chunks        │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Build Prompt    │
│ - Small Model?  │
│   ├─ Simple     │
│   │  Template   │
│   └─ Limited    │
│      Context    │
│ - Large Model?  │
│   ├─ Full       │
│   │  Template   │
│   └─ Full       │
│      Context    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Generate Response│
│ - Calculate     │
│   Safe Tokens   │
│ - Format Prompt │
│ - Run LLM       │
│ - Handle Errors │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Parse Response  │
│ - Try JSON      │
│ - Fallback to   │
│   Simple Parse  │
│ - Extract       │
│   Structure     │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Return Response │
│ - Model Info    │
│ - Timing        │
│ - Retrieved     │
│   Chunks        │
│ - Structured    │
│   Result        │
└─────────────────┘
```

### 3. MULTI-AGENT QUERY (/query_plus)
```
User Sends Query
        │
        ▼
┌─────────────────┐
│ PLANNER AGENT   │
│ - Get Base      │
│   Context       │
│ - Generate      │
│   Task Spec     │
│ - Parse JSON    │
│   Spec          │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ ITERATION LOOP  │
│ (max_loops)     │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Refined Retrieval│
│ - Combine Query │
│   + Signals     │
│ - Get Targeted  │
│   Chunks        │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Generate        │
│ Candidates      │
│ (num_samples)   │
│ - Use Coder     │
│   Agent         │
│ - Parse Each    │
│   Candidate     │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ JUDGE AGENT     │
│ - Score Each    │
│   Candidate     │
│ - Evaluate      │
│   Quality       │
│ - Parse Verdict │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Select Best     │
│ - Sort by Score │
│ - Update Best   │
│ - Early Stop?   │
│   (score ≥ 85)  │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Return Enhanced │
│ Response        │
│ - Best Candidate│
│ - Planner Spec  │
│ - Judge Score   │
└─────────────────┘
```

### 4. PATCH APPLICATION (/apply)
```
User Sends Diff
        │
        ▼
┌─────────────────┐
│ Validate Diff   │
│ - Check Format  │
│ - Security      │
│   Check         │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Apply Patch     │
│ - Write Temp    │
│   File          │
│ - Run Patch     │
│   Command       │
│ - Parse Output  │
│ - Clean Up      │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Return Results  │
│ - Changed Files │
│ - Error Info    │
└─────────────────┘
```

## Component Interactions

### Repository Indexing Flow
```
Repository Files
        │
        ▼
┌─────────────────┐
│ File Filtering  │
│ - Check Extensions│
│ - Skip Ignored  │
│   Directories   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Text Chunking   │
│ - Split Files   │
│ - Add Overlap   │
│ - Preserve      │
│   Metadata      │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Embedding       │
│ Generation      │
│ - Use Sentence  │
│   Transformers  │
│ - Normalize     │
│   Vectors       │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ FAISS Index     │
│ Construction    │
│ - Build Index   │
│ - Store         │
│   Metadata      │
└─────────────────┘
```

### Model Loading Flow
```
Model Configuration
        │
        ▼
┌─────────────────┐
│ Load Tokenizer  │
│ - AutoTokenizer │
│ - Add Padding   │
│   Token         │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Load Model      │
│ - Check Device  │
│ - Set Data Type │
│ - Apply         │
│   Quantization  │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Configure       │
│ Generation      │
│ - Set Max Tokens│
│ - Set Device    │
│ - Ready for     │
│   Inference     │
└─────────────────┘
```

## Data Structures

### Chunk Structure
```
Chunk {
    path: str          # File path
    start: int         # Start position
    end: int           # End position
    text: str          # Code content
}
```

### Query Request
```
QueryRequest {
    prompt: str        # User query
    top_k: int         # Number of chunks to retrieve
    max_new_tokens: int # Max tokens to generate
    temperature: float  # Generation temperature
}
```

### Query Response
```
QueryResponse {
    model: str         # Model name
    took_ms: int       # Processing time
    retrieved: int     # Number of chunks retrieved
    result: {          # Structured result
        analysis: str
        plan: str
        changes: [{
            path: str
            rationale: str
            diff: str
        }]
    }
}
```

## Error Handling Flow
```
Error Occurs
        │
        ▼
┌─────────────────┐
│ Error Type?     │
│ - Tokenizer     │
│ - Generation    │
│ - Parsing       │
│ - Network       │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Handle Error    │
│ - Log Error     │
│ - Return        │
│   Fallback      │
│ - Continue      │
│   Processing    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Return Response │
│ - Error Info    │
│ - Partial       │
│   Results       │
└─────────────────┘
```

This flow diagram shows the complete end-to-end process of how RepoCoder processes user queries and generates intelligent code analysis and suggestions.
