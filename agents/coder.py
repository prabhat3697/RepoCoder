"""
Coder Agent - Implements the plan step by step
Reads code, understands style, generates changes
"""

import json
import os
from typing import Dict, List, Any
from dataclasses import dataclass
from rich.console import Console

from .planner import PlanStep

console = Console()


@dataclass
class CodeChange:
    """Represents a code change"""
    file_path: str
    change_type: str  # "modify", "create", "delete"
    original_code: str
    new_code: str
    diff: str
    reasoning: str


@dataclass
class StepExecution:
    """Result of executing a plan step"""
    step_number: int
    success: bool
    changes: List[CodeChange]
    issues: List[str]
    warnings: List[str]


class CoderAgent:
    """
    Coder Agent implements code changes.
    
    Process:
    1. Read current code
    2. Understand code style
    3. Generate changes
    4. Create diffs
    5. Validate syntax
    """
    
    def __init__(self, llm, context_retriever, indexer, repo_root):
        self.llm = llm
        self.context_retriever = context_retriever
        self.indexer = indexer
        self.repo_root = repo_root
        
        self.coder_prompt = """You are an expert software engineer implementing code changes.

Your responsibilities:
1. Read and understand existing code
2. Follow the project's code style exactly
3. Generate clean, maintainable code
4. Create proper diffs
5. Add comments where needed

When implementing:
- Keep changes minimal and focused
- Follow existing patterns and conventions
- Handle edge cases
- Write defensive code
- Add proper error handling

Return JSON with:
{
  "changes": [
    {
      "file_path": "path/to/file.rb",
      "change_type": "modify|create|delete",
      "new_code": "the complete new code",
      "reasoning": "why this change is needed",
      "diff": "unified diff format"
    }
  ],
  "issues": ["any problems encountered"],
  "warnings": ["things to watch out for"]
}"""
    
    def execute_step(self, step: PlanStep, plan_context: str) -> StepExecution:
        """Execute a single plan step"""
        
        console.print(f"\n[bold cyan]═══ CODER AGENT: Step {step.step_number} ═══[/]")
        console.print(f"[cyan]Task:[/] {step.description}")
        
        # Step 1: Read files that need to be modified
        current_code = self._read_current_code(step.files_to_modify)
        
        # Step 2: Detect code style
        style_guide = self._detect_code_style(step.files_to_modify)
        
        # Step 3: Build implementation query
        implementation_query = self._build_implementation_query(
            step, current_code, style_guide, plan_context
        )
        
        # Step 4: Generate code
        console.print("[yellow]→ Generating code changes...[/]")
        output = self.llm.chat(
            system=self.coder_prompt,
            user=implementation_query,
            max_new_tokens=2000,
            temperature=0.1  # Low temperature for consistent code
        )
        
        # Step 5: Parse changes
        execution = self._parse_execution(output, step.step_number)
        
        console.print(f"[green]✓ Step {step.step_number} execution complete[/]")
        console.print(f"  Changes: {len(execution.changes)}")
        console.print(f"  Issues: {len(execution.issues)}")
        console.print(f"  Warnings: {len(execution.warnings)}")
        
        return execution
    
    def _read_current_code(self, files: List[str]) -> Dict[str, str]:
        """Read current code from files"""
        
        current_code = {}
        
        for filename in files:
            # Find file in indexer
            file_node = self.indexer.get_file_by_name(filename)
            if file_node:
                try:
                    with open(file_node.path, 'r', encoding='utf-8') as f:
                        current_code[filename] = f.read()
                    console.print(f"[green]✓ Read {filename} ({len(current_code[filename])} chars)[/]")
                except Exception as e:
                    console.print(f"[yellow]⚠ Could not read {filename}: {e}[/]")
            else:
                console.print(f"[yellow]⚠ File not found: {filename}[/]")
        
        return current_code
    
    def _detect_code_style(self, files: List[str]) -> str:
        """Detect code style from existing files"""
        
        # Read a few files to understand style
        style_indicators = {
            "indentation": "2 spaces",
            "naming": "snake_case",
            "comments": "Ruby-style #",
            "line_length": "80-100 chars"
        }
        
        # TODO: Actually analyze the code to detect style
        # For now, return generic Ruby style
        
        return """Code Style Guidelines:
- Indentation: 2 spaces
- Naming: snake_case for methods, CamelCase for classes
- Comments: Ruby-style # comments
- Line length: Keep under 100 characters
- Follow existing patterns in the file"""
    
    def _build_implementation_query(self, step: PlanStep, current_code: Dict[str, str],
                                   style_guide: str, plan_context: str) -> str:
        """Build the query for code generation"""
        
        query_parts = [
            f"Step {step.step_number}: {step.description}",
            "",
            f"Plan Context:\n{plan_context}",
            "",
            style_guide,
            ""
        ]
        
        # Add current code
        if current_code:
            query_parts.append("Current Code:")
            for filename, code in current_code.items():
                query_parts.append(f"\n📁 {filename}")
                query_parts.append("─" * 60)
                # Limit code length
                code_preview = code[:2000] + "..." if len(code) > 2000 else code
                query_parts.append(code_preview)
            query_parts.append("")
        
        # Files to create
        if step.files_to_create:
            query_parts.append(f"Files to create: {', '.join(step.files_to_create)}")
            query_parts.append("")
        
        query_parts.append("Generate the code changes needed to complete this step.")
        
        return "\n".join(query_parts)
    
    def _parse_execution(self, output: str, step_number: int) -> StepExecution:
        """Parse coder output into StepExecution"""
        
        try:
            # Extract JSON
            if "{" in output and "}" in output:
                start = output.find("{")
                end = output.rfind("}") + 1
                json_str = output[start:end]
                parsed = json.loads(json_str)
            else:
                raise ValueError("No JSON found")
            
            # Parse changes
            changes = []
            for change_data in parsed.get("changes", []):
                change = CodeChange(
                    file_path=change_data.get("file_path", ""),
                    change_type=change_data.get("change_type", "modify"),
                    original_code=change_data.get("original_code", ""),
                    new_code=change_data.get("new_code", ""),
                    diff=change_data.get("diff", ""),
                    reasoning=change_data.get("reasoning", "")
                )
                changes.append(change)
            
            return StepExecution(
                step_number=step_number,
                success=len(changes) > 0,
                changes=changes,
                issues=parsed.get("issues", []),
                warnings=parsed.get("warnings", [])
            )
            
        except Exception as e:
            console.print(f"[red]✗ Failed to parse coder output: {e}[/]")
            return StepExecution(
                step_number=step_number,
                success=False,
                changes=[],
                issues=[f"Failed to parse output: {e}"],
                warnings=[]
            )


