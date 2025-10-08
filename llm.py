#!/usr/bin/env python3
"""
Local LLM wrapper for code generation and analysis.
"""

from typing import List, Dict

import torch
import tiktoken
from transformers import AutoTokenizer, AutoModelForCausalLM
from rich.console import Console

console = Console()


class LocalCoder:
    def __init__(self, model_name: str, device: str = "cpu", max_model_len: int = 1024, quantize: bool = False):
        self.model_name = model_name
        self.device = device
        console.print(f"[bold cyan]Loading model:[/] {model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        
        # Add padding token if not present
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Configure model loading based on device and quantization
        model_kwargs = {
            "low_cpu_mem_usage": True,
        }
        
        if device == "cpu":
            # Use float32 for CPU inference
            model_kwargs["torch_dtype"] = torch.float32
            model_kwargs["device_map"] = None
        else:
            # Use float16 for GPU
            model_kwargs["torch_dtype"] = torch.float16
            model_kwargs["device_map"] = "auto"
        
        if quantize and device != "cpu":
            # Enable quantization for smaller memory footprint (only on GPU)
            model_kwargs["load_in_8bit"] = True
            console.print("[yellow]Using 8-bit quantization for smaller memory footprint[/]")
        elif quantize and device == "cpu":
            console.print("[yellow]Quantization skipped on CPU - not supported[/]")
        
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        
        # Move to device if not using device_map
        if device != "auto" and not (quantize and device != "cpu"):
            self.model = self.model.to(device)
        
        self.max_model_len = max_model_len
        self.enc = tiktoken.get_encoding("cl100k_base") if "cl100k_base" in tiktoken.list_encoding_names() else None
        console.print(f"[green]Model loaded on {device}.[/]")

    def chat(self, system: str, user: str, max_new_tokens: int = 256, temperature: float = 0.2, top_p: float = 0.9) -> str:
        # Truncate inputs for small models
        max_input_length = max(50, self.max_model_len - max_new_tokens - 50)  # Ensure positive value
        
        # Debug information
        console.print(f"[blue]Debug:[/] max_model_len={self.max_model_len}, max_new_tokens={max_new_tokens}, max_input_length={max_input_length}")
        
        # Qwen-specific format
        if "qwen" in self.model_name.lower():
            console.print("[cyan]→ Detected Qwen model, using Qwen-specific format[/]")
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
            # Use Qwen's chat template if available
            try:
                prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                console.print("[green]✓ Using Qwen tokenizer chat template[/]")
            except Exception as e:
                # Fallback: Simple instruct format for Qwen
                console.print(f"[yellow]⚠ Chat template not available, using simple format: {e}[/]")
                # Qwen 2.5 Coder prefers this simpler format
                prompt = f"You are a helpful coding assistant.\n\n### Instruction:\n{user}\n\n### Response:\n"
        # Simple prompt format for small models
        elif "dialogpt" in self.model_name.lower() or "gpt2" in self.model_name.lower():
            # Use simple format for GPT-2 based models
            prompt = f"{system}\n\nUser: {user}\nAssistant:"
        else:
            # Try to use chat format if supported
            try:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
                prompt = self._format_chat(messages)
            except:
                # Fallback to simple format
                prompt = f"{system}\n\nUser: {user}\nAssistant:"
        
        # For very small models, use even simpler format
        if self.max_model_len <= 1024:
            # Truncate system prompt for small models
            if len(system) > 200:
                system = system[:200] + "..."
            prompt = f"{system}\n\n{user}\n\nResponse:"
        
        # Truncate prompt if too long (character-based truncation)
        if len(prompt) > max_input_length * 4:  # Rough estimate: 4 chars per token
            prompt = prompt[:max_input_length * 4]
        
        # Print the final prompt being sent to the model
        console.print("\n[bold cyan]" + "="*80 + "[/]")
        console.print("[bold cyan]FINAL PROMPT BEING SENT TO MODEL:[/]")
        console.print("[bold cyan]" + "="*80 + "[/]")
        console.print(f"[yellow]{prompt}[/]")
        console.print("[bold cyan]" + "="*80 + "[/]\n")
        
        # Use a safe max_length for tokenization
        safe_max_length = min(max_input_length, 512)  # Cap at 512 to be safe
        
        console.print(f"[blue]→ Tokenizing with max_length={safe_max_length}[/]")
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=safe_max_length)
        
        # Move to device
        if hasattr(self.model, 'device'):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        else:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Use the requested max_new_tokens without artificial limits
        # Let the model generate as much as it needs
        actual_max_tokens = max_new_tokens
        
        console.print(f"[blue]→ Generating with max_new_tokens={actual_max_tokens} (no limits), temperature={temperature}[/]")
        
        with torch.no_grad():
            try:
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=actual_max_tokens,
                    do_sample=temperature > 0,
                    temperature=temperature,
                    top_p=top_p,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.1,  # Reduce repetition
                )
                console.print("[green]✓ Generation complete[/]")
            except Exception as e:
                console.print(f"[red]✗ Generation error:[/] {e}")
                # Return a simple fallback response
                return "I apologize, but I encountered an error while generating a response. Please try with a shorter prompt or different parameters."
        
        console.print(f"[blue]→ Decoding output (length: {len(outputs[0])} tokens)[/]")
        
        # First decode WITH special tokens to see the structure
        out_with_tokens = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        # Then decode without special tokens for cleaner output
        out = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        console.print("\n[bold cyan]" + "="*80 + "[/]")
        console.print("[bold cyan]RAW MODEL OUTPUT (with tokens):[/]")
        console.print("[bold cyan]" + "="*80 + "[/]")
        console.print(f"[dim]{out_with_tokens[:500]}...[/]")  # Show first 500 chars
        console.print("[bold cyan]" + "="*80 + "[/]\n")
        
        console.print("\n[bold cyan]" + "="*80 + "[/]")
        console.print("[bold cyan]RAW MODEL OUTPUT (clean):[/]")
        console.print("[bold cyan]" + "="*80 + "[/]")
        console.print(f"[green]{out[:500]}...[/]")  # Show first 500 chars
        console.print("[bold cyan]" + "="*80 + "[/]\n")
        
        # Extract the assistant's response
        # For Qwen format: look for the assistant's response after special tokens
        if "<|im_start|>assistant" in out_with_tokens:
            console.print("[cyan]→ Found Qwen assistant marker in output[/]")
            # Split by the assistant marker and take everything after it
            parts = out_with_tokens.split("<|im_start|>assistant")
            if len(parts) > 1:
                response = parts[-1].strip()
                # Remove the end token if present
                response = response.replace("<|im_end|>", "").strip()
                console.print(f"[green]✓ Extracted assistant response using tokens (length: {len(response)} chars)[/]")
                return response
        
        # Try to find where the actual response starts by looking for common patterns
        # The prompt ends and response begins, usually after "Provide your analysis in JSON format."
        if "Provide your analysis in JSON format." in out:
            console.print("[cyan]→ Found prompt end marker[/]")
            parts = out.split("Provide your analysis in JSON format.")
            if len(parts) > 1:
                response = parts[-1].strip()
                console.print(f"[green]✓ Extracted response after prompt (length: {len(response)} chars)[/]")
                return response
        
        # Try to strip the prompt if it's in the output
        if prompt in out:
            response = out[len(prompt):].strip()
            console.print(f"[blue]→ Stripped prompt from output (length: {len(response)} chars)[/]")
            return response
        
        # If output starts with "assistant" or similar, remove it
        for prefix in ["assistant\n", "assistant ", "Assistant\n", "Assistant "]:
            if out.startswith(prefix):
                response = out[len(prefix):].strip()
                console.print(f"[blue]→ Removed '{prefix}' prefix (length: {len(response)} chars)[/]")
                return response
        
        # Last resort: return as-is
        console.print(f"[yellow]⚠ Using raw output as-is (length: {len(out)} chars)[/]")
        return out.strip()

    def _format_chat(self, messages: List[Dict[str, str]]) -> str:
        # DeepSeek/ChatML-ish format
        parts = []
        for m in messages:
            role = m["role"].upper()
            parts.append(f"<|{role}|>\n{m['content']}\n")
        parts.append("<|ASSISTANT|>\n")
        return "".join(parts)
