# Running RepoCoder with Small Models on Local PC

This guide helps you run RepoCoder on a local PC with limited resources using small, efficient models.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run with Default Small Models

```bash
python app.py --repo /path/to/your/repo --use-small-models
```

## 📊 Recommended Small Models

### Code Generation Models (Choose one)

| Model | Size | RAM Usage | Quality | Best For |
|-------|------|-----------|---------|----------|
| `microsoft/DialoGPT-small` | 117M | ~500MB | Basic | Simple conversations |
| `gpt2` | 124M | ~500MB | Basic | General text generation |
| `distilgpt2` | 82M | ~350MB | Basic | Very low memory |
| `microsoft/CodeGPT-small-py` | 124M | ~500MB | Good | Python code |
| `Salesforce/codegen-350M-mono` | 350M | ~1.5GB | Better | Code generation |

### Embedding Models (Choose one)

| Model | Size | RAM Usage | Quality | Best For |
|-------|------|-----------|---------|----------|
| `sentence-transformers/all-MiniLM-L6-v2` | 22M | ~100MB | Good | General embeddings |
| `sentence-transformers/all-MiniLM-L12-v2` | 33M | ~150MB | Better | Better quality |
| `sentence-transformers/paraphrase-MiniLM-L6-v2` | 22M | ~100MB | Good | Semantic similarity |

## ⚙️ Configuration Options

### Basic Usage

```bash
# Use smallest models
python app.py --repo /path/to/repo \
  --model gpt2 \
  --embed-model sentence-transformers/all-MiniLM-L6-v2 \
  --max-model-len 512 \
  --max-chunk-chars 400
```

### With Quantization (Even Smaller Memory)

```bash
# Use quantized models for 50% less memory
python app.py --repo /path/to/repo \
  --model gpt2 \
  --embed-model sentence-transformers/all-MiniLM-L6-v2 \
  --quantize \
  --max-model-len 512
```

### CPU-Only Configuration

```bash
# Force CPU usage (default for small models)
python app.py --repo /path/to/repo \
  --device cpu \
  --model distilgpt2 \
  --embed-model sentence-transformers/all-MiniLM-L6-v2
```

## 🎯 Performance Optimization

### Memory Optimization

1. **Use Quantization**: Add `--quantize` flag
2. **Reduce Context**: Lower `--max-model-len` (e.g., 512, 256)
3. **Smaller Chunks**: Reduce `--max-chunk-chars` (e.g., 400, 200)
4. **Single Sample**: Use `--num-samples 1` and `--max-loops 1`

### Speed Optimization

1. **CPU Threads**: Set `OMP_NUM_THREADS=4` (adjust based on your CPU)
2. **Batch Size**: Models automatically use small batch sizes
3. **Disable Multi-Agent**: Use `/query` instead of `/query_plus`

## 📝 Example Commands

### Minimal Setup (Lowest Resources)

```bash
export OMP_NUM_THREADS=2
python app.py --repo /path/to/repo \
  --model distilgpt2 \
  --embed-model sentence-transformers/all-MiniLM-L6-v2 \
  --max-model-len 256 \
  --max-chunk-chars 200 \
  --num-samples 1 \
  --max-loops 1 \
  --quantize
```

### Balanced Setup (Better Quality)

```bash
export OMP_NUM_THREADS=4
python app.py --repo /path/to/repo \
  --model microsoft/CodeGPT-small-py \
  --embed-model sentence-transformers/all-MiniLM-L12-v2 \
  --max-model-len 512 \
  --max-chunk-chars 400 \
  --num-samples 1 \
  --max-loops 1
```

### Code-Focused Setup

```bash
python app.py --repo /path/to/repo \
  --model Salesforce/codegen-350M-mono \
  --embed-model sentence-transformers/all-MiniLM-L6-v2 \
  --max-model-len 1024 \
  --max-chunk-chars 600
```

## 🔧 Environment Variables

```bash
# Set these for better performance
export OMP_NUM_THREADS=4          # CPU threads
export TOKENIZERS_PARALLELISM=false # Avoid tokenizer warnings
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128  # Memory management
```

## 📊 Expected Performance

### Hardware Requirements

| Setup | RAM | CPU | Speed | Quality |
|-------|-----|-----|-------|---------|
| Minimal | 2GB | 2 cores | Slow | Basic |
| Balanced | 4GB | 4 cores | Medium | Good |
| Code-focused | 6GB | 4+ cores | Medium | Better |

### Response Times

- **Simple queries**: 5-15 seconds
- **Code analysis**: 10-30 seconds
- **Multi-agent queries**: 30-60 seconds

## 🐛 Troubleshooting

### Out of Memory

```bash
# Try smaller models
--model distilgpt2
--embed-model sentence-transformers/all-MiniLM-L6-v2

# Reduce context
--max-model-len 256
--max-chunk-chars 200

# Use quantization
--quantize
```

### Slow Performance

```bash
# Increase CPU threads
export OMP_NUM_THREADS=8

# Use smaller models
--model distilgpt2

# Disable multi-agent
# Use /query instead of /query_plus
```

### Poor Quality

```bash
# Use better models (if you have more RAM)
--model microsoft/CodeGPT-small-py
--embed-model sentence-transformers/all-MiniLM-L12-v2

# Increase context
--max-model-len 1024
--max-chunk-chars 600
```

## 🎯 API Usage Examples

### Simple Query

```bash
curl -X POST 'http://localhost:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Explain this function", "top_k": 5, "max_new_tokens": 100}'
```

### Code Analysis

```bash
curl -X POST 'http://localhost:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Find bugs in this code", "top_k": 8, "max_new_tokens": 200}'
```

## 💡 Tips for Best Results

1. **Start Small**: Begin with `distilgpt2` and `all-MiniLM-L6-v2`
2. **Monitor Resources**: Watch RAM and CPU usage
3. **Adjust Gradually**: Increase model size if you have resources
4. **Use Specific Prompts**: Be clear and specific in your requests
5. **Limit Context**: Keep queries focused and concise

## 🔄 Model Comparison

Test different models to find the best balance for your hardware:

```bash
# Test 1: Minimal
python app.py --repo /path/to/repo --model distilgpt2 --embed-model sentence-transformers/all-MiniLM-L6-v2

# Test 2: Balanced  
python app.py --repo /path/to/repo --model gpt2 --embed-model sentence-transformers/all-MiniLM-L12-v2

# Test 3: Code-focused
python app.py --repo /path/to/repo --model microsoft/CodeGPT-small-py --embed-model sentence-transformers/all-MiniLM-L6-v2
```

Choose the setup that provides the best balance of speed, memory usage, and quality for your specific use case!
