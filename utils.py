#!/usr/bin/env python3
"""
Utility functions for RepoCoder API.
"""

import os
import pathlib
import subprocess
from typing import List

from indexer import Chunk


def make_context(chunks: List[Chunk], repo_root: str, file_references: List = None) -> str:
    """Create a Cursor-style formatted context string from retrieved chunks."""
    lines = []
    
    # Group chunks by file for better organization
    file_groups = {}
    for chunk in chunks:
        file_path = chunk.path
        if file_path not in file_groups:
            file_groups[file_path] = []
        file_groups[file_path].append(chunk)
    
    # Sort files to prioritize referenced files
    sorted_files = sorted(file_groups.keys())
    if file_references:
        # Put referenced files first
        referenced_files = [ref.full_path for ref in file_references if ref.full_path in file_groups]
        for ref_file in referenced_files:
            if ref_file in sorted_files:
                sorted_files.remove(ref_file)
                sorted_files.insert(0, ref_file)
    
    chunk_num = 1
    for file_path in sorted_files:
        file_chunks = file_groups[file_path]
        rel_path = os.path.relpath(file_path, repo_root)
        filename = os.path.basename(file_path)
        
        # File header (Cursor-style)
        lines.append(f"📁 {filename}")
        lines.append(f"📂 {rel_path}")
        lines.append("─" * 80)
        
        for chunk in file_chunks:
            # Chunk header
            header = f"📍 Lines {chunk.start}-{chunk.end}"
            body = chunk.text
            
            # Clean up the text (remove our embedding headers)
            if "FILE:" in body and "---" in body:
                # Remove the embedding header we added
                parts = body.split("---\n", 1)
                if len(parts) > 1:
                    body = parts[1]
            
            # Truncate if too long
            if len(body) > 1600:
                body = body[:1600] + "\n...<truncated>..."
            
            lines.append(header)
            lines.append(body)
            lines.append("")  # Empty line between chunks
        
        lines.append("")  # Empty line between files
    
    return "\n".join(lines)


def apply_unified_diff(repo_root: str, diff_text: str) -> List[str]:
    """Apply a unified diff to files under repo_root. Returns list of changed paths.
    For safety, this is a minimal parser that shell-outs to `patch` when available,
    or raises if not. You can harden this as needed.
    """
    tmp = pathlib.Path(repo_root) / ".repcoder.patch"
    tmp.write_text(diff_text, encoding="utf-8")
    try:
        res = subprocess.run(["patch", "-p0", "-i", str(tmp)], cwd=repo_root, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"patch failed: {res.stderr}\n{res.stdout}")
        changed = []
        for line in (res.stdout or "").splitlines():
            if line.startswith("patching file "):
                changed.append(line.replace("patching file ", "").strip())
        return changed
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
