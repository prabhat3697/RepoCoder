#!/usr/bin/env python3
"""
Test script to verify configuration structure without dependencies.
"""

import sys
import os

def test_file_structure():
    """Test that all required files exist."""
    print("Testing file structure...")
    
    required_files = [
        "app.py",
        "config.py", 
        "models.py",
        "indexer.py",
        "llm.py",
        "prompts.py",
        "utils.py",
        "requirements.txt",
        "SMALL_MODELS_GUIDE.md",
        "README.md"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✅ {file} exists")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files exist!")
    return True

def test_syntax():
    """Test that Python files have valid syntax."""
    print("\nTesting Python syntax...")
    
    python_files = [
        "app.py",
        "config.py", 
        "models.py",
        "indexer.py",
        "llm.py",
        "prompts.py",
        "utils.py"
    ]
    
    import py_compile
    
    for file in python_files:
        try:
            py_compile.compile(file, doraise=True)
            print(f"✅ {file} syntax OK")
        except py_compile.PyCompileError as e:
            print(f"❌ {file} syntax error: {e}")
            return False
    
    print("✅ All Python files have valid syntax!")
    return True

def test_config_content():
    """Test that config.py has the expected small model defaults."""
    print("\nTesting configuration content...")
    
    try:
        with open("config.py", "r") as f:
            content = f.read()
        
        # Check for small model defaults
        checks = [
            ('microsoft/DialoGPT-small', "Default model is set to small model"),
            ('sentence-transformers/all-MiniLM-L6-v2', "Default embedding model is small"),
            ('default="cpu"', "Default device is CPU"),
            ('--max-model-len", type=int, default=1024', "Default max model length is reduced"),
            ('--max-chunk-chars", type=int, default=800', "Default chunk size is reduced"),
            ('--num-samples", type=int, default=1', "Default samples is reduced"),
            ('--max-loops", type=int, default=1', "Default loops is reduced"),
            ('--quantize', "Quantization option is available"),
        ]
        
        for check, description in checks:
            if check in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - not found")
                return False
        
        print("✅ Configuration has expected small model defaults!")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config.py: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing RepoCoder Small Models Setup (No Dependencies)\n")
    
    success = True
    success &= test_file_structure()
    success &= test_syntax()
    success &= test_config_content()
    
    if success:
        print("\n🎉 All tests passed! RepoCoder is configured for small models.")
        print("\n📖 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Read the guide: SMALL_MODELS_GUIDE.md")
        print("3. Run with small models: python app.py --repo /path/to/repo --use-small-models")
        print("\n💡 Recommended minimal setup:")
        print("   python app.py --repo /path/to/repo \\")
        print("     --model distilgpt2 \\")
        print("     --embed-model sentence-transformers/all-MiniLM-L6-v2 \\")
        print("     --max-model-len 512 \\")
        print("     --quantize")
    else:
        print("\n❌ Some tests failed. Please check the setup.")
        sys.exit(1)
