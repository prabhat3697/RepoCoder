#!/bin/bash
# Start RepoCoder for VM with large models

echo "🚀 Starting RepoCoder for VM with Large Models"
echo "==============================================="

# Set environment variables for VM
export ENVIRONMENT="vm"
export MODELS="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct,codellama/CodeLlama-7b-Instruct-hf"
export PRIMARY_MODEL="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
export EMBED_MODEL="jinaai/jina-embeddings-v2-base-code"

# Start the server with VM-optimized settings
python app.py \
    --repo /path/to/your/repo \
    --environment vm \
    --models deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct codellama/CodeLlama-7b-Instruct-hf \
    --primary-model deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
    --embed-model jinaai/jina-embeddings-v2-base-code \
    --max-chunk-chars 1600 \
    --chunk-overlap 200 \
    --max-model-len 4096 \
    --device auto \
    --enable-routing \
    --host 0.0.0.0 \
    --port 8000 \
    --force-rebuild
