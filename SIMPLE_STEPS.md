# RepoCoder: What Our Software Does (Simple Steps)

## 🎯 What RepoCoder Does
RepoCoder is an AI-powered code analysis tool that reads your code repository and helps you:
- Find security vulnerabilities (like SQL injection)
- Suggest code improvements
- Generate fixes and patches
- Answer questions about your code

## 📋 Step-by-Step Process

### 🚀 **STARTUP (When you run the software)**

1. **Parse Command Line**
   - Reads your settings (which model to use, repository path, etc.)
   - Sets up small model defaults for local PC

2. **Load AI Models**
   - Downloads and loads a small language model (like DialoGPT-small)
   - Loads an embedding model for searching code
   - Optimizes for CPU usage (no GPU needed)

3. **Index Your Repository**
   - Scans all code files in your repository
   - Breaks code into small chunks (800 characters each)
   - Creates a searchable database of your code
   - Builds a vector index for fast searching

4. **Start Web Server**
   - Launches a web API server (usually on port 8000)
   - Sets up endpoints for different types of requests

### 🔍 **WHEN YOU ASK A QUESTION (Single Agent Mode)**

5. **Receive Your Query**
   - You send: "Find SQL injection risks in login handler"
   - System validates your request

6. **Search for Relevant Code**
   - Converts your question into a search vector
   - Finds the most relevant code chunks from your repository
   - Retrieves 12 most similar code pieces

7. **Build the Prompt**
   - For small models: Uses simple, short prompts
   - For large models: Uses detailed, complex prompts
   - Combines your question with the relevant code

8. **Generate AI Response**
   - Sends prompt to the AI model
   - AI analyzes the code and generates suggestions
   - Handles errors gracefully if generation fails

9. **Parse and Format Response**
   - Tries to extract structured information (analysis, plan, changes)
   - If AI returns simple text, parses it into structured format
   - Returns JSON response with findings

### 🧠 **WHEN YOU USE ADVANCED MODE (Multi-Agent)**

10. **Planner Agent**
    - First AI agent analyzes your request
    - Creates a detailed plan of what needs to be done
    - Identifies specific files and methods to focus on

11. **Coder Agent (Multiple Times)**
    - Second AI agent generates multiple solution candidates
    - Each candidate is a different approach to solving the problem
    - Creates 2-5 different potential fixes

12. **Judge Agent**
    - Third AI agent evaluates each candidate
    - Scores each solution (0-100)
    - Identifies the best approach

13. **Iterative Improvement**
    - Repeats steps 10-12 up to 2 times
    - Each iteration refines the search and improves results
    - Stops early if a high-quality solution is found

14. **Return Best Solution**
    - Returns the highest-scoring solution
    - Includes the planning details and evaluation scores

### 🔧 **WHEN YOU APPLY A FIX**

15. **Receive Patch**
    - You send a code diff (unified diff format)
    - System validates the patch format

16. **Apply Changes**
    - Writes patch to temporary file
    - Uses system `patch` command to apply changes
    - Tracks which files were modified

17. **Return Results**
    - Reports which files were changed
    - Returns any errors if patch application failed

## 🏗️ **Key Components**

### **Repository Indexer**
- **What it does**: Converts your code into a searchable database
- **How**: Breaks code into chunks, creates embeddings, builds FAISS index
- **Result**: Fast similarity search across your entire codebase

### **Local LLM Wrapper**
- **What it does**: Interfaces with AI models
- **How**: Handles different model types, optimizes for CPU/GPU, manages memory
- **Result**: Reliable AI text generation

### **Prompt Templates**
- **What it does**: Provides structured prompts for different AI roles
- **How**: Simple prompts for small models, complex prompts for large models
- **Result**: Consistent, high-quality AI responses

### **Utility Functions**
- **What it does**: Helper functions for formatting and patch application
- **How**: Formats code context, applies patches safely
- **Result**: Clean, usable output

## 📊 **Performance Characteristics**

### **Memory Usage**
- Small models: 1-3 GB RAM
- Large models: 10-40 GB RAM
- With quantization: 50% less memory

### **Speed**
- Simple queries: 5-15 seconds
- Code analysis: 10-30 seconds
- Multi-agent analysis: 30-60 seconds

### **Accuracy**
- Small models: Basic analysis, good for simple tasks
- Large models: Detailed analysis, complex reasoning
- Multi-agent: Highest quality, most thorough

## 🔒 **Safety Features**

- **Input validation**: Checks all inputs for security
- **Patch safety**: Can disable automatic patch application
- **Error handling**: Graceful failure with helpful error messages
- **Resource limits**: Prevents memory overflow and infinite loops

## 🎛️ **Configuration Options**

### **Model Selection**
- **Tiny**: distilgpt2 (82M parameters) - Fastest, basic quality
- **Small**: gpt2 (124M parameters) - Balanced speed/quality
- **Code-focused**: CodeGPT-small-py - Better for code analysis

### **Performance Tuning**
- **Chunk size**: Larger chunks = more context, more memory
- **Context length**: Longer context = better analysis, slower processing
- **Retrieval count**: More chunks = more comprehensive, slower

## 🎯 **Real-World Example**

**You ask**: "Find SQL injection risks in the login handler"

**System does**:
1. Searches your codebase for login-related code
2. Finds authentication handlers, database queries
3. AI analyzes the code for SQL injection patterns
4. Returns: "Found vulnerability in login.py line 45 - uses string concatenation instead of parameterized queries"
5. Suggests: "Replace with prepared statements"
6. Provides: Exact code diff to fix the issue

**Result**: You get actionable security advice with specific fixes for your codebase!

This is how RepoCoder transforms your code repository into an intelligent, searchable knowledge base that can help you write better, more secure code.
