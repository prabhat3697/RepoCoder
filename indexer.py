#!/usr/bin/env python3
"""
Repository indexing and retrieval functionality.
"""

import os
import pathlib
from dataclasses import dataclass
from typing import List, Dict, Tuple
import numpy as np

import torch
from sentence_transformers import SentenceTransformer
from rich.console import Console

from config import CODE_EXTS, IGNORE_DIRS

console = Console()


@dataclass
class Chunk:
    path: str
    start: int
    end: int
    text: str


class RepoIndexer:
    """Fallback indexer using simple cosine similarity (no FAISS)."""
    def __init__(self, repo_root: str, embed_model_name: str, max_chunk_chars: int = 1600, overlap: int = 200):
        self.repo_root = str(pathlib.Path(repo_root).resolve())
        self.embedder = SentenceTransformer(embed_model_name, device="cuda" if torch.cuda.is_available() else "cpu")
        self.max_chunk = max_chunk_chars
        self.overlap = overlap
        self.chunks: List[Chunk] = []
        self.embeddings: List[np.ndarray] = []
        console.print("[yellow]Using fallback indexer (no FAISS/ShibuDB)[/]")

    def _should_index(self, path: pathlib.Path) -> bool:
        if any(part in IGNORE_DIRS for part in path.parts):
            return False
        return path.suffix.lower() in CODE_EXTS

    def _read_text(self, path: pathlib.Path) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def _chunk_text(self, text: str, path: str) -> List[Chunk]:
        chunks = []
        n = len(text)
        i = 0
        while i < n:
            j = min(i + self.max_chunk, n)
            piece = text[i:j]
            if piece.strip():
                chunks.append(Chunk(path=path, start=i, end=j, text=piece))
            if j >= n:
                break
            i = j - self.overlap
            i = max(i, 0)
            if i >= n:
                break
        return chunks

    def build(self) -> None:
        console.print(f"[bold cyan]Building fallback index for:[/] {self.repo_root}")
        files = []
        for p in pathlib.Path(self.repo_root).rglob("*"):
            if p.is_file() and self._should_index(p):
                files.append(p)
        console.print(f"Found {len(files)} files to index.")

        all_texts = []
        self.chunks = []
        for fpath in files:
            text = self._read_text(fpath)
            if not text:
                continue
            chunks = self._chunk_text(text, str(fpath))
            self.chunks.extend(chunks)
            all_texts.extend(self._prep_embed_text(c) for c in chunks)

        console.print(f"Chunked into {len(self.chunks)} pieces. Embedding…")
        embeddings = self.embedder.encode(all_texts, show_progress_bar=False, normalize_embeddings=True)
        
        # Store embeddings for simple cosine similarity (no FAISS)
        self.embeddings = [emb for emb in embeddings]
        
        console.print("[green]Fallback index built (no FAISS/ShibuDB).[/]")

    def _prep_embed_text(self, c: Chunk) -> str:
        header = f"PATH: {os.path.relpath(c.path, self.repo_root)}\nSPAN: {c.start}-{c.end}\n---\n"
        return header + c.text

    def retrieve(self, query: str, top_k: int = 12) -> List[Chunk]:
        if not self.embeddings:
            raise RuntimeError("Index is empty. Build it first.")
        
        # Encode query
        q_emb = self.embedder.encode([query], normalize_embeddings=True)[0]
        
        # Calculate cosine similarities
        similarities = []
        for i, emb in enumerate(self.embeddings):
            # Cosine similarity for normalized vectors
            similarity = np.dot(q_emb, emb)
            similarities.append((similarity, i))
        
        # Sort by similarity and get top_k
        similarities.sort(reverse=True)
        top_indices = [idx for _, idx in similarities[:top_k]]
        
        # Return chunks
        return [self.chunks[idx] for idx in top_indices]
