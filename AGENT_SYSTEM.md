# Multi-Agent Feature Implementation System

## 🎯 Overview

RepoCoder now has a **Cursor-style multi-agent system** for implementing features, just like Cursor Agent!

```
User Request → Planner → Coder → Judge → Executor
                  ↓         ↓       ↓        ↓
               Creates    Impl    Reviews  Applies
                 Plan     Code    Changes  to Repo
```

---

## 🤖 The Four Agents

### 1. **PLANNER Agent** 📋
**Role:** Creates detailed execution plan

**Process:**
1. Understands the user request
2. Reads relevant code to understand current implementation
3. Breaks down into steps
4. Identifies files to modify/create
5. Defines acceptance criteria

**Example Output:**
```json
{
  "goal": "Add rate limiting to API with tests",
  "steps": [
    {
      "step_number": 1,
      "description": "Add rate limiting middleware to API controller",
      "files_to_modify": ["app/controllers/api_controller.rb"],
      "files_to_create": ["app/middleware/rate_limiter.rb"],
      "dependencies": [],
      "estimated_complexity": "medium"
    },
    {
      "step_number": 2,
      "description": "Write RSpec tests for rate limiting",
      "files_to_create": ["spec/middleware/rate_limiter_spec.rb"],
      "dependencies": [1],
      "estimated_complexity": "simple"
    }
  ],
  "tests_required": true,
  "style_guidelines": "Follow Ruby style guide, use RSpec",
  "acceptance_criteria": [
    "Rate limiting works correctly",
    "Tests pass",
    "No breaking changes"
  ]
}
```

---

### 2. **CODER Agent** 💻
**Role:** Implements each step of the plan

**Process:**
1. Reads current code from files
2. Detects and follows code style
3. Generates new code
4. Creates diffs
5. Explains reasoning

**Example Output:**
```json
{
  "changes": [
    {
      "file_path": "app/middleware/rate_limiter.rb",
      "change_type": "create",
      "new_code": "class RateLimiter\n  def initialize...",
      "reasoning": "Created rate limiter following Ruby conventions",
      "diff": "... unified diff ..."
    }
  ],
  "issues": [],
  "warnings": ["Consider adding Redis backend for distributed rate limiting"]
}
```

---

### 3. **JUDGE Agent** ⚖️
**Role:** Reviews and validates code changes

**Process:**
1. Checks if plan is followed
2. Reviews code quality
3. Validates style consistency
4. Identifies issues
5. Approves or requests revision

**Example Output:**
```json
{
  "approved": true,
  "score": 0.85,
  "feedback": [
    "Code follows Ruby conventions",
    "Good error handling",
    "Tests are comprehensive"
  ],
  "issues_found": [],
  "suggestions": [
    "Consider adding documentation",
    "Could extract constants"
  ],
  "requires_revision": false
}
```

---

### 4. **EXECUTOR Agent** 🚀
**Role:** Applies changes to repository (optional)

**Process:**
1. Writes changes to files
2. Creates git branch
3. Commits changes
4. Creates pull request (optional)

**Example Output:**
```json
{
  "success": true,
  "files_modified": ["app/controllers/api_controller.rb"],
  "files_created": ["app/middleware/rate_limiter.rb", "spec/middleware/rate_limiter_spec.rb"],
  "branch_created": "feature/add-rate-limiting",
  "commit_hash": "a1b2c3d4",
  "pr_url": ""
}
```

---

## 🚀 How to Use

### Start the Server

```bash
python app.py \
  --repo ~/learn_source/Db/shibudb.org \
  --models Qwen/Qwen2.5-Coder-7B-Instruct \
  --device cuda \
  --max-model-len 4096
```

### Use the Multi-Agent System

```bash
# POST to /implement endpoint (not /query)
curl -X POST http://localhost:8000/implement \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Add a rollback task to deploy.rb with error handling and tests",
    "top_k": 30
  }'
```

---

## 📊 Complete Example

### Request:
```bash
curl -X POST http://localhost:8000/implement \
  -d '{
    "prompt": "Add rate limiting to API endpoints, write tests, follow Ruby style"
  }'
```

### Response:
```json
{
  "model": "MultiAgent",
  "result": {
    "plan": {
      "goal": "Add rate limiting to API endpoints with tests",
      "steps": 3,
      "estimated_time": "1-3 hours"
    },
    "executions": [
      {
        "step": 1,
        "success": true,
        "changes": 2,
        "issues": []
      },
      {
        "step": 2,
        "success": true,
        "changes": 1,
        "issues": []
      },
      {
        "step": 3,
        "success": true,
        "changes": 1,
        "issues": []
      }
    ],
    "judgements": [
      {
        "step": 1,
        "approved": true,
        "score": 0.9,
        "issues": []
      },
      {
        "step": 2,
        "approved": true,
        "score": 0.85,
        "issues": []
      },
      {
        "step": 3,
        "approved": true,
        "score": 0.95,
        "issues": []
      }
    ],
    "summary": {
      "total_steps": 3,
      "successful_steps": 3,
      "failed_steps": 0,
      "all_approved": true
    },
    "success": true
  }
}
```

---

## 🔄 The Complete Workflow

```
1. User sends request: "Add feature X with tests"
   ↓

2. PLANNER Agent
   • Reads relevant code
   • Understands current implementation
   • Creates step-by-step plan
   • Identifies files to modify/create
   ↓

3. For each step:
   
   a) CODER Agent
      • Reads current code
      • Detects code style
      • Generates changes
      • Creates diffs
      ↓
   
   b) JUDGE Agent
      • Reviews changes
      • Checks quality
      • Validates style
      • Approves or rejects
      ↓
   
   c) If rejected
      • CODER revises (up to 2 times)
      • JUDGE reviews again
      ↓

4. After all steps approved:
   
   EXECUTOR Agent (optional)
   • Applies changes to files
   • Creates git branch
   • Commits changes
   • Creates PR
```

---

## 🎯 Features

### ✅ **Intelligent Planning**
- Reads relevant code first
- Understands dependencies
- Breaks into manageable steps

### ✅ **Style-Aware Coding**
- Detects project conventions
- Follows existing patterns
- Maintains consistency

### ✅ **Quality Assurance**
- Every change is reviewed
- Multiple revision attempts
- High quality bar

### ✅ **Safe Execution**
- Creates separate branch
- Doesn't auto-apply by default
- You review before merging

---

## 📝 Example Requests

### Simple Feature
```bash
curl -X POST http://localhost:8000/implement \
  -d '{"prompt": "Add a rollback task to deploy.rb"}'
```

### Feature with Tests
```bash
curl -X POST http://localhost:8000/implement \
  -d '{"prompt": "Add input validation to user registration with RSpec tests"}'
```

### Feature with Style Requirements
```bash
curl -X POST http://localhost:8000/implement \
  -d '{"prompt": "Refactor database layer following repository pattern, add tests, follow Ruby style guide"}'
```

### Complex Feature
```bash
curl -X POST http://localhost:8000/implement \
  -d '{"prompt": "Implement OAuth2 authentication with JWT tokens, add refresh token support, write comprehensive tests, follow existing auth patterns"}'
```

---

## 🔧 Configuration

### Enable Auto-Apply (Dangerous!)
```python
# In app.py, change:
executor = ExecutorAgent(repo_root, auto_commit=True, auto_pr=False)

# Then:
orchestrator.execute_feature_request(user_request, query_analysis, auto_apply=True)
```

### Adjust Revision Attempts
```python
# In agents/orchestrator.py
self.max_revisions = 3  # Try up to 3 times before giving up
```

---

## 📊 Comparison: /query vs /implement

| Feature | /query | /implement |
|---------|--------|------------|
| **Purpose** | Understand code | Modify code |
| **Agents** | Single LLM | Multi-agent (4) |
| **Output** | Analysis, explanation | Plan + Code + Review |
| **Modifies Files** | No | Yes (optional) |
| **Time** | ~2-5s | ~30-60s |
| **Use Case** | "How does X work?" | "Add feature X" |

---

## 🎯 When to Use Each

### Use `/query` for:
- ✅ Understanding code
- ✅ Debugging issues
- ✅ Finding code
- ✅ Code review
- ✅ General questions

### Use `/implement` for:
- ✅ Adding features
- ✅ Refactoring code
- ✅ Implementing changes
- ✅ Creating tests
- ✅ Major modifications

---

## 🚀 What You Get

Just like Cursor Agent, you get:
- ✅ **Detailed Plan** before any code is written
- ✅ **Step-by-step execution** with progress
- ✅ **Code review** for every change
- ✅ **Multiple revisions** if quality isn't good enough
- ✅ **Git integration** (branches, commits, PRs)
- ✅ **Safe by default** (doesn't auto-apply)

Your RepoCoder is now a **full-featured AI coding assistant**! 🎉


