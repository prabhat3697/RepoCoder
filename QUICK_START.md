# RepoCoder - Quick Start Guide

## 🚀 Get Started in 3 Minutes

### 1. Install Dependencies

```bash
pip install fastapi uvicorn pydantic transformers accelerate torch \
    sentence-transformers tiktoken rich numpy
```

### 2. Start RepoCoder

```bash
python app.py \
  --repo ~/learn_source/Db/shibudb.org \
  --models Qwen/Qwen2.5-Coder-7B-Instruct \
  --device cuda \
  --max-model-len 4096
```

**Expected Output:**
```
═══ RepoCoder Starting ═══
Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
✓ Embedding model loaded
Loading primary LLM: Qwen/Qwen2.5-Coder-7B-Instruct
✓ LLM loaded
Initializing CoreIndexer for: /Users/.../shibudb.org
Building file tree...
Built file tree: 245 files
Extracting code chunks...
Extracted 1,234 code chunks
Computing embeddings for chunks...
Computed embeddings for 1,234 chunks

✓ Index Built Successfully!
  Files: 245/245
  Chunks: 1234
  Languages: 8

═══ RepoCoder Ready! ═══
Repository: /Users/.../shibudb.org
Models: Qwen/Qwen2.5-Coder-7B-Instruct
API: http://localhost:8000/docs
```

### 3. Send Your First Query

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "How does deploy.rb deploy my app?",
    "top_k": 20
  }'
```

---

## 📝 Example Queries

### Understanding Code (ANALYSIS)

```bash
# How does a file work?
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "How does deploy.rb deploy my app?"}'

# Explain a function
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Explain the authentication flow in auth.rb"}'

# What does this do?
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "What does the database.yml configuration do?"}'
```

### Debugging (DEBUG)

```bash
# Fix a bug
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Fix the login bug in users_controller.rb"}'

# Why is something failing?
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Why is the deployment failing?"}'

# Troubleshoot
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Debug the connection timeout in database.rb"}'
```

### Making Changes (CHANGES)

```bash
# Add a feature
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Add input validation to the user registration form"}'

# Refactor code
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Refactor the database connection logic"}'

# Implement something
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Implement password reset functionality"}'
```

### Code Review (REVIEW)

```bash
# Review code
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Review the security in auth_controller.rb"}'

# Check best practices
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Check for SQL injection vulnerabilities"}'

# Validate implementation
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Validate error handling in api.rb"}'
```

### Finding Code (SEARCH)

```bash
# Find functions
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Find all API endpoints"}'

# Locate code
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Where is the authentication logic?"}'

# Show all instances
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "Show all database queries"}'
```

### General Questions (GENERAL)

```bash
# Repository info
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "How many files are in the project?"}'

# List files
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "List all configuration files"}'

# Project structure
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "What is the project structure?"}'
```

---

## 🌐 Web UI

Visit http://localhost:8000/docs for the interactive Swagger UI:

1. Click on `/query` endpoint
2. Click "Try it out"
3. Enter your query in the JSON body
4. Click "Execute"
5. See the response!

---

## 📊 Check Statistics

```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "repo_root": "/Users/.../shibudb.org",
  "indexer": {
    "total_files": 245,
    "code_files": 245,
    "total_chunks": 1234,
    "languages": 8
  },
  "models_available": 1,
  "models": ["Qwen/Qwen2.5-Coder-7B-Instruct"]
}
```

---

## 🔧 Configuration Options

### Use Different Model

```bash
python app.py \
  --repo ~/myrepo \
  --models deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
  --device cuda
```

### Use Better Embedding Model

```bash
python app.py \
  --repo ~/myrepo \
  --embed-model jinaai/jina-embeddings-v2-base-code
```

### CPU-Only Mode

```bash
python app.py \
  --repo ~/myrepo \
  --models microsoft/DialoGPT-small \
  --device cpu \
  --max-model-len 1024
```

### Retrieve More Context

```bash
curl -X POST http://localhost:8000/query \
  -d '{"prompt": "...", "top_k": 30}'  # Default is 20
```

---

## 🎯 Understanding the Response

```json
{
  "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
  
  // Performance metrics
  "took_ms": 1500,
  "retrieved": 3,
  
  // Main response
  "result": {
    "analysis": "deploy.rb uses Capistrano...",
    "plan": "The deployment process...",
    "changes": [],  // Code changes (if any)
    "confidence": 0.95
  },
  
  // Query understanding
  "query_analysis": {
    "intent": "analysis",  // ANALYSIS, DEBUG, CHANGES, etc.
    "complexity": "medium",  // simple, medium, complex
    "file_references": [
      {"filename": "deploy.rb", "confidence": 0.9}
    ],
    "entities": ["deploy", "app"]  // Extracted entities
  },
  
  // Retrieval details
  "retrieval": {
    "strategy": "hybrid",  // file_specific, semantic, or hybrid
    "files_involved": 1,
    "total_chunks": 3
  }
}
```

---

## 🐛 Troubleshooting

### Model Download Issues

```bash
# Pre-download models
python -c "from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen2.5-Coder-7B-Instruct')"
```

### Memory Issues

```bash
# Use smaller model
python app.py --repo ~/myrepo --models microsoft/DialoGPT-small --max-model-len 1024

# Or use CPU
python app.py --repo ~/myrepo --device cpu
```

### Slow Indexing

```bash
# Check how many files are being indexed
curl http://localhost:8000/stats

# Reduce max-chunk-chars in core/indexer.py if needed
```

---

## 📚 Next Steps

1. **Explore**: Try different query types
2. **Customize**: Modify `core/` modules for your needs
3. **Extend**: Add custom retrieval strategies or LLM integrations
4. **Deploy**: Use in production with proper GPU setup

---

## 💡 Tips

- Use **specific file names** for better results: "How does deploy.rb work?"
- Be **clear about intent**: "Debug", "Explain", "Add", "Review"
- **Adjust top_k** for more/less context: `"top_k": 30`
- Check **query_analysis** in response to see how your query was understood
- Use the **Web UI** at `/docs` for interactive exploration

---

**You're all set!** Start querying your code! 🚀

