#!/bin/bash
# Start RepoCoder for local development with small models

echo "🚀 Starting RepoCoder for Local Development"
echo "============================================="

# Set environment variables for local development
export ENVIRONMENT="local"
export MODELS="microsoft/DialoGPT-small,microsoft/CodeGPT-small-py"
export PRIMARY_MODEL="microsoft/DialoGPT-small"
export EMBED_MODEL="sentence-transformers/all-MiniLM-L6-v2"

# Start the server with local-optimized settings
python app.py \
    --repo /Users/pawasthi/learn_source/repocoder \
    --environment local \
    --models microsoft/DialoGPT-small microsoft/CodeGPT-small-py \
    --primary-model microsoft/DialoGPT-small \
    --embed-model sentence-transformers/all-MiniLM-L6-v2 \
    --max-chunk-chars 800 \
    --chunk-overlap 100 \
    --max-model-len 1024 \
    --device cpu \
    --enable-routing \
    --host 0.0.0.0 \
    --port 8000 \
    --force-rebuild
