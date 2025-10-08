# Best Models for LLM-Based Routing

## 🎯 Problem with DialoGPT

**DialoGPT is NOT good for routing** because:
- ❌ Designed for conversations, not instruction-following
- ❌ Doesn't generate structured JSON
- ❌ Just echoes the prompt

---

## ✅ Recommended Small Models for Routing

### 🥇 Best Overall: TinyLlama (Recommended!)

```bash
python app.py \
  --repo ~/myrepo \
  --device cuda \
  --use-llm-routing \
  --routing-model TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

**Why TinyLlama:**
- ✅ Instruction-following (trained for it!)
- ✅ Small: 1.1B parameters (~2.2GB)
- ✅ Fast: ~200ms per routing decision
- ✅ Good at JSON generation
- ✅ Can run on CPU

---

### 🥈 Second Choice: Phi-2

```bash
python app.py \
  --repo ~/myrepo \
  --device cuda \
  --use-llm-routing \
  --routing-model microsoft/phi-2
```

**Why Phi-2:**
- ✅ Very intelligent (2.7B parameters)
- ✅ Excellent instruction-following
- ✅ Great at structured output
- ❌ Larger: ~5.4GB
- ❌ Slower: ~500ms

---

### 🥉 Third Choice: GPT-2

```bash
python app.py \
  --repo ~/myrepo \
  --device cuda \
  --use-llm-routing \
  --routing-model gpt2
```

**Why GPT-2:**
- ✅ Small: 124M parameters (~500MB)
- ✅ Very fast: ~100ms
- ⚠️ Decent at instruction-following
- ❌ Not great at JSON

---

## 🚫 Models to AVOID for Routing

### ❌ DialoGPT-small/medium/large
- Designed for chat, not instructions
- Doesn't generate, just echoes

### ❌ DistilBERT
- Designed for classification, not generation
- Can't generate text

### ❌ BERT-based models
- Encoder-only, can't generate

---

## 💡 Recommendation

### For CPU:
```bash
# Use pattern-based routing (no extra model)
python app.py --repo ~/myrepo --device cpu
```

### For GPU with extra VRAM:
```bash
# Use TinyLlama for intelligent routing
python app.py \
  --repo ~/myrepo \
  --device cuda \
  --use-llm-routing \
  --routing-model TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

### For Maximum Intelligence:
```bash
# Use Phi-2 for routing (needs more VRAM)
python app.py \
  --repo ~/myrepo \
  --device cuda \
  --use-llm-routing \
  --routing-model microsoft/phi-2
```

---

## 📊 Performance Comparison

| Model | Size | Speed | Quality | Recommendation |
|-------|------|-------|---------|----------------|
| **TinyLlama** | 2.2GB | 200ms | ⭐⭐⭐⭐ | ✅ Best choice |
| **Phi-2** | 5.4GB | 500ms | ⭐⭐⭐⭐⭐ | For extra intelligence |
| **GPT-2** | 500MB | 100ms | ⭐⭐⭐ | If memory is limited |
| **Pattern-Based** | 0MB | <10ms | ⭐⭐⭐ | Default (no model) |
| ~~DialoGPT~~ | 500MB | N/A | ⭐ | ❌ Don't use |

---

## 🎯 Current Recommendation

**Use pattern-based routing (default)** - it's working well!

The pattern-based router already handles:
- ✅ Metadata queries → Direct computation
- ✅ File-specific queries → Only target files
- ✅ Semantic queries → Search all code

Only enable LLM routing if you have **TinyLlama or Phi-2** available and need to handle very complex/ambiguous queries.

---

## 🔧 How to Switch

### From Pattern to LLM:
```bash
# Just add --use-llm-routing
python app.py --repo ~/myrepo --use-llm-routing
```

### From LLM to Pattern:
```bash
# Remove --use-llm-routing
python app.py --repo ~/myrepo
```

Both work! Pattern-based is the recommended default. 🚀

