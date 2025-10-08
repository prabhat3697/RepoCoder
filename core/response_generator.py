"""
Response Generator - Generates responses using selected models
"""

import json
import os
from typing import Dict, Any
from rich.console import Console

from .types import QueryAnalysis, RetrievalContext, ModelConfig, Response

console = Console()


class ResponseGenerator:
    """
    Generates responses by:
    1. Building appropriate prompts
    2. Formatting context
    3. Executing model
    4. Formatting output
    """
    
    def __init__(self, llm_executor=None):
        self.llm_executor = llm_executor
    
    def generate(self, query_analysis: QueryAnalysis, context: RetrievalContext, 
                model_config: ModelConfig, repo_root: str) -> Response:
        """Generate response for a query"""
        console.print(f"[cyan]Generating response using {model_config.name}...[/]")
        
        # Build prompt
        system_prompt = self._build_system_prompt(query_analysis)
        user_prompt = self._build_user_prompt(query_analysis, context, repo_root)
        
        # Let the model generate as much as it needs (use model's full capacity)
        # Don't artificially limit the response
        max_tokens = model_config.max_tokens // 2  # Use half of context for generation
        
        console.print(f"[cyan]→ Requesting {max_tokens} max_new_tokens from model (no artificial limits)[/]")
        
        if self.llm_executor:
            output = self.llm_executor.chat(
                system=system_prompt,
                user=user_prompt,
                max_new_tokens=max_tokens,
                temperature=model_config.temperature
            )
        else:
            # Fallback: return formatted context
            output = self._fallback_response(query_analysis, context)
        
        # Parse response
        response = self._parse_response(output, model_config.name)
        
        console.print(f"[green]Response generated successfully[/]")
        return response
    
    def _build_system_prompt(self, query_analysis: QueryAnalysis) -> str:
        """Build system prompt based on query intent"""
        
        base_prompt = "You are RepoCoder, a senior software engineer analyzing a codebase.\n"
        
        intent_prompts = {
            "analysis": "Focus on explaining code functionality, purpose, and structure.",
            "debug": "Focus on identifying issues, errors, and suggesting fixes.",
            "changes": "Focus on proposing code changes, additions, and modifications.",
            "review": "Focus on code quality, best practices, and improvements.",
            "search": "Focus on locating relevant code and explaining findings.",
            "general": "Provide helpful information about the codebase."
        }
        
        intent_prompt = intent_prompts.get(query_analysis.intent.value, intent_prompts["general"])
        
        return base_prompt + intent_prompt + "\n\nReturn a JSON response with keys: analysis, plan, changes."
    
    def _build_user_prompt(self, query_analysis: QueryAnalysis, context: RetrievalContext, 
                          repo_root: str) -> str:
        """Build user prompt with context"""
        
        # Format context
        formatted_context = self._format_context(context, repo_root)
        
        # Build prompt
        prompt_parts = [
            f"Task: {query_analysis.original_query}",
            "",
            f"Context ({context.total_chunks} relevant code chunks):",
            formatted_context,
        ]
        
        if query_analysis.file_references:
            files = ", ".join(ref.filename for ref in query_analysis.file_references)
            prompt_parts.append(f"\nFiles mentioned: {files}")
        
        prompt_parts.append("\nProvide your analysis in JSON format.")
        
        return "\n".join(prompt_parts)
    
    def _format_context(self, context: RetrievalContext, repo_root: str) -> str:
        """Format retrieval context for prompt"""
        lines = []
        
        # Group chunks by file
        file_chunks = {}
        for chunk in context.chunks:
            if chunk.file_path not in file_chunks:
                file_chunks[chunk.file_path] = []
            file_chunks[chunk.file_path].append(chunk)
        
        # Format each file's chunks
        for file_path, chunks in file_chunks.items():
            # Get filename
            filename = os.path.basename(file_path)
            
            lines.append(f"\n📁 {filename}")
            lines.append("─" * 60)
            
            for chunk in chunks:
                lines.append(f"\n📍 Lines {chunk.start_line}-{chunk.end_line}")
                lines.append(chunk.content)
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _parse_response(self, output: str, model_name: str) -> Response:
        """Parse model output into Response object"""
        
        console.print(f"[cyan]→ Parsing model output (length: {len(output)} chars)[/]")
        
        # Sometimes the model wraps JSON in ```json ... ``` - extract it
        if "```json" in output:
            console.print("[yellow]→ Found JSON code block, extracting...[/]")
            start = output.find("```json") + 7
            end = output.find("```", start)
            if end > start:
                output = output[start:end].strip()
                console.print(f"[green]✓ Extracted JSON from code block (length: {len(output)} chars)[/]")
        
        # Try to find JSON object in the output
        if "{" in output and "}" in output:
            # Extract everything from first { to last }
            start = output.find("{")
            end = output.rfind("}") + 1
            json_str = output[start:end]
            console.print(f"[cyan]→ Attempting to parse JSON (length: {len(json_str)} chars)[/]")
        else:
            json_str = output
        
        # Try to parse as JSON
        try:
            parsed = json.loads(json_str)
            console.print(f"[green]✓ Successfully parsed JSON response[/]")
            return Response(
                analysis=parsed.get("analysis", ""),
                plan=parsed.get("plan", ""),
                changes=parsed.get("changes", []),
                model_used=model_name,
                confidence=0.8
            )
        except json.JSONDecodeError as e:
            console.print(f"[red]✗ JSON parsing failed: {e}[/]")
            console.print(f"[yellow]→ Falling back to plain text response[/]")
            # Fallback: treat as plain text
            return Response(
                analysis=output,
                plan="",
                changes=[],
                model_used=model_name,
                confidence=0.5,
                metadata={"format": "plain_text"}
            )
    
    def _fallback_response(self, query_analysis: QueryAnalysis, context: RetrievalContext) -> str:
        """Generate fallback response when no LLM is available"""
        
        response = {
            "analysis": f"Found {context.total_chunks} relevant code chunks for query: {query_analysis.original_query}",
            "plan": f"Strategy used: {context.strategy_used}",
            "changes": []
        }
        
        if context.file_tree:
            files = ", ".join(f.name for f in context.file_tree)
            response["analysis"] += f"\n\nFiles involved: {files}"
        
        return json.dumps(response, indent=2)

