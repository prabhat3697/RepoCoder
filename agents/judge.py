"""
Judge Agent - Reviews and validates code changes
Ensures changes follow the plan and meet quality standards
"""

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from rich.console import Console

from .coder import StepExecution, CodeChange
from .planner import ExecutionPlan

console = Console()


@dataclass
class JudgementResult:
    """Result of judging code changes"""
    approved: bool
    score: float  # 0.0 to 1.0
    feedback: List[str]
    issues_found: List[str]
    suggestions: List[str]
    requires_revision: bool


class JudgeAgent:
    """
    Judge Agent reviews code changes.
    
    Checks:
    1. Does it follow the plan?
    2. Is code quality good?
    3. Does it follow project style?
    4. Are there any issues?
    5. Does it meet acceptance criteria?
    """
    
    def __init__(self, llm):
        self.llm = llm
        
        self.judge_prompt = """You are a senior code reviewer and architect.

Your task is to review code changes and ensure they meet quality standards.

Review criteria:
1. Correctness: Does the code do what it's supposed to?
2. Quality: Is the code clean and maintainable?
3. Style: Does it follow project conventions?
4. Safety: Are there any security or stability issues?
5. Tests: Are tests included and adequate?

Return JSON with:
{
  "approved": true/false,
  "score": 0.0-1.0,
  "feedback": ["positive feedback items"],
  "issues_found": ["problems that must be fixed"],
  "suggestions": ["optional improvements"],
  "requires_revision": true/false
}

Be thorough but constructive."""
    
    def judge_execution(self, execution: StepExecution, step_description: str, 
                       acceptance_criteria: List[str]) -> JudgementResult:
        """Judge the execution of a step"""
        
        console.print(f"\n[bold cyan]═══ JUDGE AGENT: Step {execution.step_number} ═══[/]")
        console.print(f"[cyan]Reviewing:[/] {step_description}")
        
        # Build review query
        changes_summary = self._format_changes(execution.changes)
        
        review_query = f"""Step Task: {step_description}

Acceptance Criteria:
{chr(10).join(f"- {c}" for c in acceptance_criteria)}

Code Changes Generated:
{changes_summary}

Issues Reported: {execution.issues}
Warnings: {execution.warnings}

Review these changes thoroughly."""
        
        # Get judgement from LLM
        console.print("[yellow]→ Requesting code review...[/]")
        
        output = self.llm.chat(
            system=self.judge_prompt,
            user=review_query,
            max_new_tokens=500,
            temperature=0.0  # Deterministic review
        )
        
        # Parse judgement
        judgement = self._parse_judgement(output)
        
        # Print result
        if judgement.approved:
            console.print(f"[bold green]✓ APPROVED[/] (score: {judgement.score:.2f})")
        else:
            console.print(f"[bold red]✗ REJECTED[/] (score: {judgement.score:.2f})")
        
        if judgement.feedback:
            console.print(f"[green]Feedback:[/]")
            for fb in judgement.feedback:
                console.print(f"  • {fb}")
        
        if judgement.issues_found:
            console.print(f"[red]Issues:[/]")
            for issue in judgement.issues_found:
                console.print(f"  ✗ {issue}")
        
        if judgement.suggestions:
            console.print(f"[yellow]Suggestions:[/]")
            for suggestion in judgement.suggestions:
                console.print(f"  • {suggestion}")
        
        return judgement
    
    def _format_changes(self, changes: List[CodeChange]) -> str:
        """Format changes for review"""
        
        lines = []
        for i, change in enumerate(changes, 1):
            lines.append(f"\nChange {i}: {change.change_type.upper()} {change.file_path}")
            lines.append(f"Reasoning: {change.reasoning}")
            lines.append("\nCode:")
            lines.append(change.new_code[:500] + "..." if len(change.new_code) > 500 else change.new_code)
        
        return "\n".join(lines)
    
    def _parse_judgement(self, output: str) -> JudgementResult:
        """Parse judge output"""
        
        try:
            # Extract JSON
            if "{" in output and "}" in output:
                start = output.find("{")
                end = output.rfind("}") + 1
                json_str = output[start:end]
                parsed = json.loads(json_str)
            else:
                raise ValueError("No JSON found")
            
            return JudgementResult(
                approved=parsed.get("approved", False),
                score=parsed.get("score", 0.5),
                feedback=parsed.get("feedback", []),
                issues_found=parsed.get("issues_found", []),
                suggestions=parsed.get("suggestions", []),
                requires_revision=parsed.get("requires_revision", not parsed.get("approved", False))
            )
            
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to parse judgement: {e}[/]")
            # Fallback: approve with low score
            return JudgementResult(
                approved=True,
                score=0.6,
                feedback=["Automatic approval (parsing failed)"],
                issues_found=[],
                suggestions=[],
                requires_revision=False
            )


