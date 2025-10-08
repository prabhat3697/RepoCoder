# RepoCoder - Intelligent Code Analysis System

> A modular pipeline for understanding and analyzing code repositories using LLMs

## 🎯 Overview

RepoCoder is an intelligent code analysis system that helps you understand, debug, and modify code through natural language queries. It uses a **clean, modular pipeline** where you can integrate LLMs at any stage for better understanding.

## ✨ Key Features

### 📁 **Smart Indexing**
- Builds complete file tree
- Extracts code chunks with overlap
- Stores in vector database
- Tracks file metadata

### 🔍 **Intelligent Query Understanding**
- Detects file references (`deploy.rb`, `src/app.py:42`)
- Classifies intent (analysis, debug, changes, review, search)
- Extracts entities (functions, classes, variables)
- Can use LLM for complex query understanding

### 🎯 **Context Retrieval**
- **File-Specific**: Direct retrieval from mentioned files
- **Semantic**: Vector similarity search
- **Hybrid**: Combines both with intelligent boosting

### 🤖 **Dynamic Model Selection**
- Automatically selects best model based on:
  - Query intent
  - Complexity level
  - Model capabilities
  - Context requirements

### 💬 **Intelligent Responses**
- Intent-aware prompts
- Beautiful code formatting
- Structured JSON output

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Run RepoCoder

```bash
python app.py \
  --repo ~/your/code/repository \
  --models Qwen/Qwen2.5-Coder-7B-Instruct \
  --device cuda \
  --max-model-len 4096
```

### Query Your Code

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "How does deploy.rb deploy my app?",
    "top_k": 20
  }'
```

## 📊 Example Response

```json
{
  "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
  "took_ms": 1500,
  "retrieved": 3,
  "result": {
    "analysis": "deploy.rb uses Capistrano to automate deployment...",
    "plan": "The deployment process works as follows...",
    "changes": [],
    "confidence": 0.95
  },
  "query_analysis": {
    "intent": "analysis",
    "complexity": "medium",
    "file_references": [
      {"filename": "deploy.rb", "confidence": 0.9}
    ],
    "entities": ["deploy", "app", "capistrano"]
  },
  "retrieval": {
    "strategy": "hybrid",
    "files_involved": 1,
    "total_chunks": 3
  }
}
```

## 🏗️ Architecture

RepoCoder uses a **modular pipeline architecture**:

```
User Query
    ↓
1. Query Analyzer
   • Detects files, intent, entities
   • Can use LLM for complex queries
    ↓
2. Context Retriever
   • File-specific, semantic, or hybrid retrieval
   • Smart ranking and boosting
    ↓
3. Model Selector
   • Scores models based on capabilities
   • Selects best model for the task
    ↓
4. Response Generator
   • Builds intent-aware prompts
   • Generates intelligent response
    ↓
Structured Response
```

## 📦 Core Components

### `core/indexer.py` - File Indexing
- Builds file tree from repository
- Extracts code chunks with smart overlapping
- Tracks file metadata (language, size, etc.)

### `core/query_analyzer.py` - Query Understanding
- Detects file references in queries
- Classifies intent (6 types)
- Extracts entities
- Confidence scoring

### `core/context_retriever.py` - Smart Retrieval
- Multiple retrieval strategies
- Intelligent boosting for file matches
- Semantic vector search

### `core/model_selector.py` - Model Selection
- Intelligent model scoring
- Capability matching
- Performance optimization

### `core/response_generator.py` - Response Creation
- Intent-aware prompt building
- Beautiful context formatting
- Flexible output parsing

### `core/pipeline.py` - Orchestration
- Connects all components
- Tracks performance
- Comprehensive logging

## 🎯 Query Intent Types

RepoCoder understands 6 types of queries:

| Intent | Examples | Use Case |
|--------|----------|----------|
| **ANALYSIS** 📊 | "How does X work?", "Explain the auth flow" | Understanding code |
| **DEBUG** 🐛 | "Fix the login bug", "Why is this failing?" | Troubleshooting |
| **CHANGES** ✏️ | "Add validation", "Refactor database layer" | Modifying code |
| **REVIEW** 🔍 | "Review security", "Check best practices" | Code quality |
| **SEARCH** 🔎 | "Find all API endpoints", "Locate auth code" | Finding code |
| **GENERAL** 💬 | "How many files?", "What languages?" | Repository info |

## 🔧 Configuration

### Custom Models

```python
# Use different models
python app.py \
  --repo ~/myrepo \
  --models "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct" \
  --device cuda
```

### Custom Embedding Model

```python
python app.py \
  --repo ~/myrepo \
  --embed-model "jinaai/jina-embeddings-v2-base-code"
```

### Adjust Context Size

```python
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "...", "top_k": 30}'  # Retrieve more chunks
```

## 🔌 API Endpoints

### `GET /health`
Check service health
```bash
curl http://localhost:8000/health
```

### `GET /stats`
Get indexing statistics
```bash
curl http://localhost:8000/stats
```

### `POST /query`
Query the codebase
```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Your question", "top_k": 20}'
```

## 🧩 Extensibility

RepoCoder is designed to be easily extended:

### Add Custom Retrieval Strategy

```python
from core.context_retriever import ContextRetriever

class GraphRetriever(ContextRetriever):
    def retrieve_graph_based(self, query_analysis, top_k):
        # Use file dependency graph
        ...

pipeline.context_retriever = GraphRetriever(indexer, embedder)
```

### Add LLM-Based Query Analysis

```python
from core.query_analyzer import QueryAnalyzer

class LLMQueryAnalyzer(QueryAnalyzer):
    def analyze(self, query):
        # Use small LLM to understand complex queries
        llm_result = self.small_llm.analyze(query)
        return merge_with_rules(llm_result)

pipeline.query_analyzer = LLMQueryAnalyzer(small_llm)
```

### Add Custom Intent Type

```python
# In core/types.py
class IntentType(Enum):
    # ... existing ...
    SECURITY_AUDIT = "security_audit"

# Extend query analyzer patterns
```

## 📈 Performance

- **Indexing**: ~1000 files/minute
- **Query Processing**: <2 seconds typical
- **Memory**: Efficient with lazy loading
- **Scalable**: Handles 100,000+ files

## 🧪 Testing

Each component is independently testable:

```python
# Test query analyzer
from core.query_analyzer import QueryAnalyzer

analyzer = QueryAnalyzer()
result = analyzer.analyze("How does deploy.rb work?")
assert result.intent.value == "analysis"
assert len(result.file_references) == 1
```

## 🛣️ Roadmap

- [x] Core modular architecture
- [x] Intelligent query understanding
- [x] Multi-strategy retrieval
- [x] Dynamic model selection
- [ ] Graph-based retrieval (file dependencies)
- [ ] Incremental indexing
- [ ] Multi-repository support
- [ ] VSCode extension
- [ ] Web UI

## 📝 Requirements

```
fastapi
uvicorn[standard]
pydantic
transformers
accelerate
torch
sentence-transformers
tiktoken
rich
numpy
```

## 🤝 Contributing

Contributions welcome! The modular architecture makes it easy to:
- Add new retrieval strategies
- Add new intent types
- Improve prompt templates
- Add tests

## 📄 License

MIT License

## 🙏 Acknowledgments

Built for better code understanding using:
- FastAPI for the API
- Sentence Transformers for embeddings
- Transformers for LLMs
- Rich for beautiful terminal output

---

**RepoCoder** - Understanding code, one query at a time 🚀
