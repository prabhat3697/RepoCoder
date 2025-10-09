"""
Planner Agent - Creates detailed execution plans
Reads relevant code to understand current implementation
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class PlanStep:
    """A single step in the execution plan"""
    step_number: int
    description: str
    files_to_modify: List[str]
    files_to_create: List[str]
    dependencies: List[int]  # Which steps must complete first
    estimated_complexity: str  # "simple", "medium", "complex"


@dataclass
class ExecutionPlan:
    """Complete execution plan for a feature request"""
    goal: str
    steps: List[PlanStep]
    files_to_read: List[str]
    tests_required: bool
    style_guidelines: str
    acceptance_criteria: List[str]
    estimated_time: str


class PlannerAgent:
    """
    Planner Agent creates detailed execution plans.
    
    Process:
    1. Understand the request
    2. Read relevant code to understand current implementation
    3. Break down into steps
    4. Identify files to modify/create
    5. Define acceptance criteria
    """
    
    def __init__(self, llm, context_retriever, indexer):
        self.llm = llm
        self.context_retriever = context_retriever
        self.indexer = indexer
        
        self.planner_prompt = """You are a senior software architect and planner.

Your task is to create a detailed execution plan for code changes.

Process:
1. Analyze the request
2. Understand current codebase structure
3. Break down into clear steps
4. Identify files to modify/create
5. Define acceptance criteria

Return a JSON plan with this structure:
{
  "goal": "Brief description of what we're building",
  "steps": [
    {
      "step_number": 1,
      "description": "What to do in this step",
      "files_to_modify": ["file1.rb", "file2.rb"],
      "files_to_create": ["new_file.rb"],
      "dependencies": [],
      "estimated_complexity": "simple|medium|complex"
    }
  ],
  "files_to_read": ["files to understand first"],
  "tests_required": true,
  "style_guidelines": "Follow existing Ruby style, use RSpec",
  "acceptance_criteria": [
    "Feature works as expected",
    "Tests pass",
    "No breaking changes"
  ]
}

Be specific and actionable."""
    
    def create_plan(self, user_request: str, query_analysis, top_k: int = 30) -> ExecutionPlan:
        """
        Create a detailed execution plan
        
        Steps:
        1. Retrieve relevant code for context
        2. Send to planner LLM
        3. Parse plan
        4. Validate plan
        """
        
        console.print(f"\n[bold cyan]═══ PLANNER AGENT ═══[/]")
        console.print(f"[cyan]Creating plan for:[/] {user_request}")
        
        # Step 1: Get context about current codebase
        console.print("[yellow]→ Reading relevant code to understand current implementation...[/]")
        context = self.context_retriever.retrieve(query_analysis, top_k)
        
        # Format code context
        code_context = self._format_code_context(context)
        
        # Step 2: Get project structure info
        stats = self.indexer.get_stats()
        file_list = [f"{f.name} ({f.language})" for f in self.indexer.file_tree[:20]]
        
        project_info = f"""Project Overview:
- Total Files: {stats['total_files']}
- Languages: {stats['languages']}
- Key Files: {', '.join(file_list)}

Current Code Structure:
{code_context}
"""
        
        # Step 3: Build planner query
        user_query = f"""Request: {user_request}

{project_info}

Create a detailed step-by-step plan to implement this request.
Consider:
- What files need to be modified
- What new files need to be created
- What tests are needed
- How to maintain code style consistency
- Dependencies between steps

Return the plan in JSON format."""
        
        # Step 4: Get plan from LLM
        console.print("[yellow]→ Generating execution plan...[/]")
        
        plan_output = self.llm.chat(
            system=self.planner_prompt,
            user=user_query,
            max_new_tokens=1000,
            temperature=0.1  # Low temperature for consistent planning
        )
        
        # Step 5: Parse plan
        plan = self._parse_plan(plan_output, user_request)
        
        console.print(f"[green]✓ Plan created with {len(plan.steps)} steps[/]")
        self._print_plan(plan)
        
        return plan
    
    def _format_code_context(self, context) -> str:
        """Format code context for planner"""
        lines = []
        
        # Group by file
        file_chunks = {}
        for chunk in context.chunks[:10]:  # Limit to avoid overwhelming planner
            if chunk.file_path not in file_chunks:
                file_chunks[chunk.file_path] = []
            file_chunks[chunk.file_path].append(chunk)
        
        for file_path, chunks in file_chunks.items():
            import os
            filename = os.path.basename(file_path)
            lines.append(f"\nFile: {filename}")
            lines.append("─" * 40)
            for chunk in chunks:
                lines.append(f"Lines {chunk.start_line}-{chunk.end_line}:")
                lines.append(chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content)
        
        return "\n".join(lines)
    
    def _parse_plan(self, output: str, user_request: str) -> ExecutionPlan:
        """Parse LLM output into ExecutionPlan"""
        
        # Extract JSON
        try:
            if "{" in output and "}" in output:
                start = output.find("{")
                end = output.rfind("}") + 1
                json_str = output[start:end]
                parsed = json.loads(json_str)
            else:
                raise ValueError("No JSON found")
            
            # Build PlanSteps
            steps = []
            for step_data in parsed.get("steps", []):
                step = PlanStep(
                    step_number=step_data.get("step_number", len(steps) + 1),
                    description=step_data.get("description", ""),
                    files_to_modify=step_data.get("files_to_modify", []),
                    files_to_create=step_data.get("files_to_create", []),
                    dependencies=step_data.get("dependencies", []),
                    estimated_complexity=step_data.get("estimated_complexity", "medium")
                )
                steps.append(step)
            
            # Build ExecutionPlan
            plan = ExecutionPlan(
                goal=parsed.get("goal", user_request),
                steps=steps,
                files_to_read=parsed.get("files_to_read", []),
                tests_required=parsed.get("tests_required", False),
                style_guidelines=parsed.get("style_guidelines", "Follow existing code style"),
                acceptance_criteria=parsed.get("acceptance_criteria", []),
                estimated_time=self._estimate_time(steps)
            )
            
            return plan
            
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to parse plan: {e}[/]")
            # Return fallback simple plan
            return self._create_fallback_plan(user_request)
    
    def _create_fallback_plan(self, user_request: str) -> ExecutionPlan:
        """Create a simple fallback plan"""
        
        return ExecutionPlan(
            goal=user_request,
            steps=[
                PlanStep(
                    step_number=1,
                    description=user_request,
                    files_to_modify=[],
                    files_to_create=[],
                    dependencies=[],
                    estimated_complexity="medium"
                )
            ],
            files_to_read=[],
            tests_required=True,
            style_guidelines="Follow existing code style",
            acceptance_criteria=["Feature works as expected"],
            estimated_time="1-2 hours"
        )
    
    def _estimate_time(self, steps: List[PlanStep]) -> str:
        """Estimate implementation time based on complexity"""
        
        total_complexity = 0
        for step in steps:
            if step.estimated_complexity == "simple":
                total_complexity += 1
            elif step.estimated_complexity == "medium":
                total_complexity += 3
            else:  # complex
                total_complexity += 8
        
        if total_complexity <= 3:
            return "30 minutes - 1 hour"
        elif total_complexity <= 10:
            return "1-3 hours"
        elif total_complexity <= 20:
            return "3-8 hours"
        else:
            return "1-2 days"
    
    def _print_plan(self, plan: ExecutionPlan):
        """Print the plan in a readable format"""
        
        console.print(f"\n[bold green]📋 Execution Plan[/]")
        console.print(f"[green]Goal:[/] {plan.goal}")
        console.print(f"[green]Estimated Time:[/] {plan.estimated_time}")
        console.print(f"[green]Tests Required:[/] {plan.tests_required}")
        
        console.print(f"\n[bold cyan]Steps ({len(plan.steps)}):[/]")
        for step in plan.steps:
            console.print(f"\n  [cyan]{step.step_number}. {step.description}[/]")
            if step.files_to_modify:
                console.print(f"     Modify: {', '.join(step.files_to_modify)}")
            if step.files_to_create:
                console.print(f"     Create: {', '.join(step.files_to_create)}")
            console.print(f"     Complexity: {step.estimated_complexity}")
        
        if plan.acceptance_criteria:
            console.print(f"\n[bold cyan]Acceptance Criteria:[/]")
            for i, criteria in enumerate(plan.acceptance_criteria, 1):
                console.print(f"  {i}. {criteria}")


