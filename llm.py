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
        
        if quantize:
            # Enable quantization for smaller memory footprint
            model_kwargs["load_in_8bit"] = True
            console.print("[yellow]Using 8-bit quantization for smaller memory footprint[/]")
        
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        
        # Move to device if not using device_map
        if device != "auto" and not quantize:
            self.model = self.model.to(device)
        
        self.max_model_len = max_model_len
        self.enc = tiktoken.get_encoding("cl100k_base") if "cl100k_base" in tiktoken.list_encoding_names() else None
        console.print(f"[green]Model loaded on {device}.[/]")

    def chat(self, system: str, user: str, max_new_tokens: int = 256, temperature: float = 0.2, top_p: float = 0.9) -> str:
        # Truncate inputs for small models
        max_input_length = max(50, self.max_model_len - max_new_tokens - 50)  # Ensure positive value
        
        # Debug information
        console.print(f"[blue]Debug:[/] max_model_len={self.max_model_len}, max_new_tokens={max_new_tokens}, max_input_length={max_input_length}")
        
        # Simple prompt format for small models
        if "dialogpt" in self.model_name.lower() or "gpt2" in self.model_name.lower():
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
        
        # Use a safe max_length for tokenization
        safe_max_length = min(max_input_length, 512)  # Cap at 512 to be safe
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=safe_max_length)
        
        # Move to device
        if hasattr(self.model, 'device'):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        else:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            try:
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=min(max_new_tokens, 256),  # Limit for small models
                    do_sample=temperature > 0,
                    temperature=temperature,
                    top_p=top_p,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.1,  # Reduce repetition
                )
            except Exception as e:
                console.print(f"[red]Generation error:[/] {e}")
                # Return a simple fallback response
                return "I apologize, but I encountered an error while generating a response. Please try with a shorter prompt or different parameters."
        
        out = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Heuristic to strip the prompt
        if prompt in out:
            return out[len(prompt):].strip()
        else:
            return out.strip()

    def _format_chat(self, messages: List[Dict[str, str]]) -> str:
        # DeepSeek/ChatML-ish format
        parts = []
        for m in messages:
            role = m["role"].upper()
            parts.append(f"<|{role}|>\n{m['content']}\n")
        parts.append("<|ASSISTANT|>\n")
        return "".join(parts)
