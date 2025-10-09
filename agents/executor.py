"""
Executor Agent - Applies code changes to repository
Creates branches, commits, and PRs
"""

import os
import subprocess
from typing import List, Dict, Any
from dataclasses import dataclass
from rich.console import Console

from .coder import CodeChange, StepExecution

console = Console()


@dataclass
class ExecutionResult:
    """Result of applying changes"""
    success: bool
    files_modified: List[str]
    files_created: List[str]
    branch_created: str
    commit_hash: str
    pr_url: str
    errors: List[str]


class ExecutorAgent:
    """
    Executor Agent applies code changes to the repository.
    
    Can:
    1. Apply code changes
    2. Create git branches
    3. Commit changes
    4. Create pull requests
    5. Run tests
    """
    
    def __init__(self, repo_root: str, auto_commit: bool = False, auto_pr: bool = False):
        self.repo_root = repo_root
        self.auto_commit = auto_commit
        self.auto_pr = auto_pr
    
    def apply_changes(self, executions: List[StepExecution], branch_name: str = None) -> ExecutionResult:
        """Apply all code changes"""
        
        console.print(f"\n[bold cyan]═══ EXECUTOR AGENT ═══[/]")
        
        files_modified = []
        files_created = []
        errors = []
        
        # Collect all changes
        all_changes = []
        for execution in executions:
            all_changes.extend(execution.changes)
        
        console.print(f"[cyan]Applying {len(all_changes)} code changes...[/]")
        
        # Apply each change
        for change in all_changes:
            try:
                result = self._apply_single_change(change)
                if result:
                    if change.change_type == "create":
                        files_created.append(change.file_path)
                    else:
                        files_modified.append(change.file_path)
                    console.print(f"[green]✓ Applied: {change.file_path}[/]")
                else:
                    errors.append(f"Failed to apply {change.file_path}")
                    console.print(f"[red]✗ Failed: {change.file_path}[/]")
            except Exception as e:
                errors.append(f"{change.file_path}: {str(e)}")
                console.print(f"[red]✗ Error applying {change.file_path}: {e}[/]")
        
        # Create branch if requested
        branch_created = ""
        commit_hash = ""
        pr_url = ""
        
        if branch_name and self.auto_commit:
            branch_created = self._create_branch(branch_name)
            if files_modified or files_created:
                commit_hash = self._commit_changes(files_modified + files_created, "Implement feature")
                
                if self.auto_pr:
                    pr_url = self._create_pr(branch_name)
        
        result = ExecutionResult(
            success=len(errors) == 0,
            files_modified=files_modified,
            files_created=files_created,
            branch_created=branch_created,
            commit_hash=commit_hash,
            pr_url=pr_url,
            errors=errors
        )
        
        self._print_execution_result(result)
        
        return result
    
    def _apply_single_change(self, change: CodeChange) -> bool:
        """Apply a single code change"""
        
        file_path = os.path.join(self.repo_root, change.file_path)
        
        try:
            if change.change_type == "create":
                # Create new file
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(change.new_code)
                return True
                
            elif change.change_type == "modify":
                # Modify existing file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(change.new_code)
                return True
                
            elif change.change_type == "delete":
                # Delete file
                if os.path.exists(file_path):
                    os.remove(file_path)
                return True
            
            return False
            
        except Exception as e:
            console.print(f"[red]Error applying change: {e}[/]")
            return False
    
    def _create_branch(self, branch_name: str) -> str:
        """Create a new git branch"""
        
        try:
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Created branch: {branch_name}[/]")
                return branch_name
            else:
                console.print(f"[yellow]⚠ Branch creation failed: {result.stderr}[/]")
                return ""
                
        except Exception as e:
            console.print(f"[yellow]⚠ Could not create branch: {e}[/]")
            return ""
    
    def _commit_changes(self, files: List[str], message: str) -> str:
        """Commit changes to git"""
        
        try:
            # Add files
            for file_path in files:
                subprocess.run(
                    ["git", "add", file_path],
                    cwd=self.repo_root,
                    check=True
                )
            
            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True
                )
                commit_hash = hash_result.stdout.strip()
                console.print(f"[green]✓ Committed: {commit_hash[:8]}[/]")
                return commit_hash
            else:
                console.print(f"[yellow]⚠ Commit failed: {result.stderr}[/]")
                return ""
                
        except Exception as e:
            console.print(f"[yellow]⚠ Could not commit: {e}[/]")
            return ""
    
    def _create_pr(self, branch_name: str) -> str:
        """Create a pull request (placeholder)"""
        
        # This would use GitHub/GitLab API
        console.print(f"[yellow]PR creation not implemented yet[/]")
        console.print(f"[yellow]To create PR manually:[/]")
        console.print(f"  git push origin {branch_name}")
        console.print(f"  Then create PR in GitHub/GitLab")
        
        return ""
    
    def _print_execution_result(self, result: ExecutionResult):
        """Print execution result"""
        
        console.print(f"\n[bold cyan]═══ Execution Result ═══[/]")
        
        if result.success:
            console.print(f"[bold green]✓ SUCCESS[/]")
        else:
            console.print(f"[bold red]✗ FAILED[/]")
        
        if result.files_modified:
            console.print(f"[green]Modified ({len(result.files_modified)}):[/]")
            for f in result.files_modified:
                console.print(f"  ✓ {f}")
        
        if result.files_created:
            console.print(f"[green]Created ({len(result.files_created)}):[/]")
            for f in result.files_created:
                console.print(f"  + {f}")
        
        if result.branch_created:
            console.print(f"[cyan]Branch:[/] {result.branch_created}")
        
        if result.commit_hash:
            console.print(f"[cyan]Commit:[/] {result.commit_hash[:8]}")
        
        if result.errors:
            console.print(f"[red]Errors ({len(result.errors)}):[/]")
            for err in result.errors:
                console.print(f"  ✗ {err}")


