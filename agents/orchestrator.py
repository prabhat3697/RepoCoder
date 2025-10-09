"""
Agent Orchestrator - Coordinates Planner → Coder → Judge → Executor workflow
"""

from typing import Dict, List, Any
from rich.console import Console

from .planner import PlannerAgent, ExecutionPlan
from .coder import CoderAgent, StepExecution
from .judge import JudgeAgent, JudgementResult
from .executor import ExecutorAgent, ExecutionResult

console = Console()


class AgentOrchestrator:
    """
    Orchestrates the multi-agent workflow:
    
    1. PLANNER creates plan
    2. CODER implements each step
    3. JUDGE reviews each step
    4. If approved → continue, else → revise
    5. EXECUTOR applies changes (optional)
    6. Repeat with feedback loop
    """
    
    def __init__(self, planner: PlannerAgent, coder: CoderAgent, 
                 judge: JudgeAgent, executor: ExecutorAgent = None):
        self.planner = planner
        self.coder = coder
        self.judge = judge
        self.executor = executor
        
        self.max_revisions = 2  # Max times to revise a step
    
    def execute_feature_request(self, user_request: str, query_analysis, 
                                auto_apply: bool = False) -> Dict[str, Any]:
        """
        Execute complete feature request through agent workflow
        
        Returns:
            {
                "plan": ExecutionPlan,
                "executions": List[StepExecution],
                "judgements": List[JudgementResult],
                "final_result": ExecutionResult (if auto_apply),
                "success": bool
            }
        """
        
        console.print(f"\n[bold magenta]{'='*80}[/]")
        console.print(f"[bold magenta]MULTI-AGENT FEATURE IMPLEMENTATION[/]")
        console.print(f"[bold magenta]{'='*80}[/]")
        console.print(f"[cyan]Request:[/] {user_request}")
        
        # Step 1: PLANNER creates plan
        plan = self.planner.create_plan(user_request, query_analysis, top_k=30)
        
        # Step 2: Execute each step with CODER and JUDGE
        executions = []
        judgements = []
        
        for step in plan.steps:
            # Try up to max_revisions times
            approved = False
            revision_count = 0
            
            while not approved and revision_count < self.max_revisions:
                # CODER implements the step
                execution = self.coder.execute_step(
                    step, 
                    plan_context=self._format_plan_context(plan)
                )
                
                # JUDGE reviews the execution
                judgement = self.judge.judge_execution(
                    execution, 
                    step.description,
                    plan.acceptance_criteria
                )
                
                if judgement.approved:
                    approved = True
                    executions.append(execution)
                    judgements.append(judgement)
                    console.print(f"[green]✓ Step {step.step_number} approved[/]")
                else:
                    revision_count += 1
                    console.print(f"[yellow]⚠ Step {step.step_number} needs revision (attempt {revision_count}/{self.max_revisions})[/]")
                    
                    if revision_count < self.max_revisions:
                        console.print("[cyan]→ Revising based on feedback...[/]")
                        # TODO: Feed judge's feedback back to coder for revision
                    else:
                        console.print(f"[red]✗ Step {step.step_number} failed after {self.max_revisions} revisions[/]")
                        executions.append(execution)
                        judgements.append(judgement)
                        break
        
        # Step 3: EXECUTOR applies changes (if requested and all approved)
        final_result = None
        all_approved = all(j.approved for j in judgements)
        
        if auto_apply and all_approved and self.executor:
            console.print("\n[yellow]→ All steps approved, applying changes...[/]")
            branch_name = self._generate_branch_name(user_request)
            final_result = self.executor.apply_changes(executions, branch_name)
        elif not all_approved:
            console.print("\n[red]⚠ Not all steps approved, skipping execution[/]")
        
        # Build result
        result = {
            "plan": {
                "goal": plan.goal,
                "steps": len(plan.steps),
                "estimated_time": plan.estimated_time
            },
            "executions": [
                {
                    "step": e.step_number,
                    "success": e.success,
                    "changes": len(e.changes),
                    "issues": e.issues
                }
                for e in executions
            ],
            "judgements": [
                {
                    "step": i + 1,
                    "approved": j.approved,
                    "score": j.score,
                    "issues": j.issues_found
                }
                for i, j in enumerate(judgements)
            ],
            "summary": {
                "total_steps": len(plan.steps),
                "successful_steps": sum(1 for j in judgements if j.approved),
                "failed_steps": sum(1 for j in judgements if not j.approved),
                "all_approved": all_approved
            },
            "success": all_approved
        }
        
        if final_result:
            result["execution"] = {
                "files_modified": final_result.files_modified,
                "files_created": final_result.files_created,
                "branch": final_result.branch_created,
                "commit": final_result.commit_hash[:8] if final_result.commit_hash else ""
            }
        
        self._print_final_summary(result)
        
        return result
    
    def _format_plan_context(self, plan: ExecutionPlan) -> str:
        """Format plan as context for coder"""
        
        lines = [
            f"Overall Goal: {plan.goal}",
            f"Total Steps: {len(plan.steps)}",
            ""
        ]
        
        for step in plan.steps:
            lines.append(f"Step {step.step_number}: {step.description}")
        
        return "\n".join(lines)
    
    def _generate_branch_name(self, user_request: str) -> str:
        """Generate a branch name from user request"""
        
        # Simple: take first few words, lowercase, join with hyphens
        words = user_request.lower().split()[:4]
        branch = "feature/" + "-".join(w for w in words if w.isalnum())
        return branch
    
    def _print_final_summary(self, result: Dict[str, Any]):
        """Print final summary"""
        
        console.print(f"\n[bold magenta]{'='*80}[/]")
        console.print(f"[bold magenta]FINAL SUMMARY[/]")
        console.print(f"[bold magenta]{'='*80}[/]")
        
        summary = result['summary']
        
        if result['success']:
            console.print(f"[bold green]✓ ALL STEPS APPROVED[/]")
        else:
            console.print(f"[bold yellow]⚠ SOME STEPS NEED WORK[/]")
        
        console.print(f"\n[cyan]Steps:[/] {summary['successful_steps']}/{summary['total_steps']} successful")
        
        if 'execution' in result:
            console.print(f"\n[cyan]Applied Changes:[/]")
            console.print(f"  Modified: {len(result['execution']['files_modified'])} files")
            console.print(f"  Created: {len(result['execution']['files_created'])} files")
            if result['execution']['branch']:
                console.print(f"  Branch: {result['execution']['branch']}")
            if result['execution']['commit']:
                console.print(f"  Commit: {result['execution']['commit']}")


