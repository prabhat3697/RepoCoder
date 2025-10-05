#!/usr/bin/env python3
"""
Test script to verify small model configuration works.
"""

import sys
import os
from config import parse_args

def test_config():
    """Test that the configuration can be parsed correctly."""
    print("Testing small model configuration...")
    
    # Test with minimal arguments
    test_args = [
        "--repo", "/tmp/test_repo",
        "--model", "gpt2",
        "--embed-model", "sentence-transformers/all-MiniLM-L6-v2",
        "--max-model-len", "512",
        "--quantize"
    ]
    
    # Temporarily replace sys.argv
    original_argv = sys.argv
    sys.argv = ["test_small_models.py"] + test_args
    
    try:
        args = parse_args()
        print("✅ Configuration parsing successful!")
        print(f"   Model: {args.model}")
        print(f"   Embed Model: {args.embed_model}")
        print(f"   Device: {args.device}")
        print(f"   Max Model Length: {args.max_model_len}")
        print(f"   Quantize: {args.quantize}")
        print(f"   Max Chunk Chars: {args.max_chunk_chars}")
        print(f"   Num Samples: {args.num_samples}")
        print(f"   Max Loops: {args.max_loops}")
        
        # Verify small model defaults
        assert args.device == "cpu", f"Expected device='cpu', got '{args.device}'"
        assert args.max_model_len == 512, f"Expected max_model_len=512, got {args.max_model_len}"
        assert args.max_chunk_chars == 800, f"Expected max_chunk_chars=800, got {args.max_chunk_chars}"
        assert args.num_samples == 1, f"Expected num_samples=1, got {args.num_samples}"
        assert args.max_loops == 1, f"Expected max_loops=1, got {args.max_loops}"
        
        print("✅ All small model defaults verified!")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    finally:
        sys.argv = original_argv
    
    return True

def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting module imports...")
    
    try:
        from config import parse_args, CODE_EXTS, IGNORE_DIRS
        print("✅ config.py imported successfully")
        
        from models import IndexRequest, QueryRequest, QueryResponse, ApplyRequest
        print("✅ models.py imported successfully")
        
        from indexer import RepoIndexer, Chunk
        print("✅ indexer.py imported successfully")
        
        from llm import LocalCoder
        print("✅ llm.py imported successfully")
        
        from prompts import SYSTEM_TEMPLATE, USER_TEMPLATE
        print("✅ prompts.py imported successfully")
        
        from utils import make_context, apply_unified_diff
        print("✅ utils.py imported successfully")
        
        print("✅ All modules imported successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing RepoCoder Small Models Configuration\n")
    
    success = True
    success &= test_config()
    success &= test_imports()
    
    if success:
        print("\n🎉 All tests passed! RepoCoder is ready for small models.")
        print("\n📖 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Read the guide: SMALL_MODELS_GUIDE.md")
        print("3. Run with small models: python app.py --repo /path/to/repo --use-small-models")
    else:
        print("\n❌ Some tests failed. Please check the configuration.")
        sys.exit(1)
