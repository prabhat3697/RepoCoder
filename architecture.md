# RepoCoder Architecture

## 🎯 Design Principles

1. **Modularity**: Each component is independent and testable
2. **Pipeline-Based**: Data flows through clear stages
3. **LLM-Augmented**: Can use LLMs at any stage for better understanding
4. **Model Agnostic**: Can swap models at any stage
5. **Incremental**: Build basic first, enhance later

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY ANALYZER                                │
│  - Parse query                                                   │
│  - Extract file references                                       │
│  - Detect intent (optional LLM)                                  │
│  - Identify query type                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INTENT CLASSIFIER                              │
│  - Analysis (explain/understand)                                 │
│  - Debug (fix/troubleshoot)                                      │
│  - Changes (add/modify/refactor)                                 │
│  - Review (check/validate)                                       │
│  - Search (find/locate)                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CONTEXT RETRIEVER                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ File Tree  │  │   Vector   │  │  Metadata  │                │
│  │   Index    │  │   Search   │  │   Store    │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│  - Get file tree structure                                       │
│  - Retrieve relevant chunks                                      │
│  - Get file metadata                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL SELECTOR                                │
│  - Select best model for intent                                  │
│  - Configure model parameters                                    │
│  - Load model if needed                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 RESPONSE GENERATOR                               │
│  - Build context from chunks                                     │
│  - Create appropriate prompt                                     │
│  - Generate response                                             │
│  - Format output                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RESPONSE                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Core Components

### 1. **Indexer** (Foundation Layer)
```
CoreIndexer
├── FileTreeBuilder      # Build directory structure
├── ChunkExtractor       # Extract code chunks
├── VectorStore          # Store embeddings (ShibuDB)
└── MetadataStore        # Store file metadata
```

**Responsibilities:**
- Scan repository
- Build file tree
- Extract code chunks (smart chunking)
- Generate embeddings
- Store in vector DB
- Track metadata (hash, mtime, etc.)

### 2. **Query Analyzer** (Understanding Layer)
```
QueryAnalyzer
├── TextParser           # Parse query text
├── FileDetector         # Detect file references
├── IntentDetector       # Detect user intent (can use LLM)
└── EntityExtractor      # Extract entities (functions, classes, etc.)
```

**Responsibilities:**
- Parse user query
- Detect file references (deploy.rb, src/app.py, etc.)
- Detect intent (analyze, debug, change, etc.)
- Extract entities (optional LLM augmentation)

### 3. **Intent Classifier** (Decision Layer)
```
IntentClassifier
├── RuleBasedClassifier  # Regex patterns
├── LLMClassifier        # Optional LLM for complex queries
└── HybridClassifier     # Combine both
```

**Intent Types:**
- **ANALYSIS**: Explain, understand, how does X work
- **DEBUG**: Fix bug, troubleshoot, why error
- **CHANGES**: Add feature, modify, refactor
- **REVIEW**: Check code, validate, improve
- **SEARCH**: Find function, locate file
- **GENERAL**: General questions

### 4. **Context Retriever** (Data Layer)
```
ContextRetriever
├── FileTreeRetriever    # Get file structure
├── VectorRetriever      # Semantic search
├── FileRetriever        # Get specific files
└── HybridRetriever      # Combine strategies
```

**Retrieval Strategies:**
- **File-Specific**: Direct file lookup
- **Semantic**: Vector similarity search
- **Hybrid**: Combine both with boosting
- **Graph-Based**: Use file relationships (imports, etc.)

### 5. **Model Selector** (Orchestration Layer)
```
ModelSelector
├── ModelRegistry        # Available models
├── SelectionStrategy    # Selection logic
└── ModelLoader          # Load models on demand
```

**Selection Criteria:**
- Query intent
- Complexity
- Model capabilities
- Performance requirements

### 6. **Response Generator** (Output Layer)
```
ResponseGenerator
├── PromptBuilder        # Build prompts
├── ContextFormatter     # Format context
├── ModelExecutor        # Execute model
└── ResponseFormatter    # Format response
```

---

## 🔧 LLM Augmentation Points

At each stage, we can optionally use LLMs for better understanding:

1. **Query Analysis**: Use small LLM to understand complex queries
2. **Intent Classification**: Use LLM when regex patterns are insufficient
3. **Entity Extraction**: Use LLM to extract functions, classes, variables
4. **Context Ranking**: Use LLM to rank retrieved chunks by relevance
5. **Response Generation**: Primary LLM for final response

---

## 📦 Data Flow Example

### Example Query: "How does deploy.rb deploy my app?"

```
1. Query Analyzer
   Input: "How does deploy.rb deploy my app?"
   Output: {
     files: ["deploy.rb"],
     intent: "ANALYSIS",
     entities: ["deploy", "app"],
     confidence: 0.9
   }

2. Intent Classifier
   Input: {intent: "ANALYSIS", ...}
   Output: {
     category: "CODE_ANALYSIS",
     subcategory: "FILE_EXPLANATION",
     recommended_model: "code-model-medium"
   }

3. Context Retriever
   Input: {files: ["deploy.rb"], ...}
   Output: {
     file_tree: ["deploy.rb", "config/deploy/*.rb"],
     chunks: [Chunk1, Chunk2, Chunk3],
     metadata: {language: "ruby", size: 1234}
   }

4. Model Selector
   Input: {category: "CODE_ANALYSIS", ...}
   Output: {
     model: "Qwen/Qwen2.5-Coder-7B-Instruct",
     params: {temperature: 0.2, max_tokens: 500}
   }

5. Response Generator
   Input: {chunks, model, prompt_template}
   Output: {
     analysis: "deploy.rb uses Capistrano to...",
     confidence: 0.95
   }
```

---

## 🚀 Implementation Phases

### Phase 1: Minimal Core (MVP)
- Basic file tree indexing
- Simple vector storage
- Regex-based query analysis
- Single model response generation

### Phase 2: Enhanced Retrieval
- Advanced chunking strategies
- Hybrid retrieval
- File relationship graph
- Metadata enrichment

### Phase 3: LLM Augmentation
- LLM-based intent classification
- Entity extraction
- Context ranking
- Multi-model orchestration

### Phase 4: Advanced Features
- Incremental indexing
- Real-time updates
- Multi-repository support
- Custom model fine-tuning

---

## 🎯 Benefits

1. **Modularity**: Each component can be tested/improved independently
2. **Flexibility**: Can swap models at any stage
3. **Scalability**: Easy to add new features
4. **Debuggability**: Clear data flow through pipeline
5. **Extensibility**: Can add new intent types, models, retrievers
6. **Performance**: Can optimize individual components

---

## 📝 Configuration Example

```yaml
indexer:
  chunk_size: 1600
  overlap: 200
  embedding_model: "jinaai/jina-embeddings-v2-base-code"

query_analyzer:
  use_llm: false  # Start simple
  llm_model: "small-classifier"  # Optional

intent_classifier:
  strategy: "rule_based"  # or "llm" or "hybrid"

model_selector:
  models:
    - name: "Qwen/Qwen2.5-Coder-7B-Instruct"
      capabilities: ["code_analysis", "code_generation"]
      max_tokens: 4096
    - name: "microsoft/DialoGPT-small"
      capabilities: ["general_qa"]
      max_tokens: 1024

retrieval:
  strategy: "hybrid"  # file + semantic
  top_k: 20
  boost_file_matches: 3.0
```

---

This architecture is clean, modular, and ready for incremental improvement!

