#!/usr/bin/env python3
"""
Utility functions for RepoCoder API.
"""

import os
import pathlib
import subprocess
from typing import List

from indexer import Chunk


def make_context(chunks: List[Chunk], repo_root: str) -> str:
    """Create a formatted context string from retrieved chunks."""
    lines = []
    for i, c in enumerate(chunks, 1):
        rel = os.path.relpath(c.path, repo_root)
        header = f"--- CHUNK {i} | {rel} | span {c.start}-{c.end} ---"
        body = c.text
        if len(body) > 1600:
            body = body[:1600] + "\n...<truncated>..."
        lines.append(header + "\n" + body)
    return "\n\n".join(lines)


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
