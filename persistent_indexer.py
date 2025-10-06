#!/usr/bin/env python3
"""
Persistent repository indexing with ShibuDB for incremental updates.
"""

import os
import json
import hashlib
import pathlib
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from shibudb_client import ShibuDbClient, connect
from rich.console import Console
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from config import CODE_EXTS, IGNORE_DIRS
from indexer import Chunk

console = Console()


@dataclass
class FileMetadata:
    """Metadata for tracking file changes."""
    path: str
    size: int
    mtime: float
    hash: str
    indexed_at: str
    chunk_count: int


class PersistentRepoIndexer:
    """Repository indexer with persistent storage using ShibuDB vector database."""
    
    def __init__(self, repo_root: str, embed_model_name: str, 
                 max_chunk_chars: int = 1600, overlap: int = 200,
                 shibudb_host: str = "localhost", shibudb_port: int = 4444):
        self.repo_root = str(pathlib.Path(repo_root).resolve())
        self.embed_model_name = embed_model_name
        self.max_chunk_chars = max_chunk_chars
        self.overlap = overlap
        
        # ShibuDB connection settings
        self.shibudb_host = shibudb_host
        self.shibudb_port = shibudb_port
        
        # Initialize ShibuDB client
        self.client = None
        self.space_name = f"repocoder_{hashlib.md5(self.repo_root.encode()).hexdigest()[:8]}"
        
        # File tracking
        self.file_metadata: Dict[str, FileMetadata] = {}
        
        # Initialize embedding model (lazy loading)
        self.embedder = None
        self.embedding_dimension = None
        
    def _get_embedder(self):
        """Lazy load the embedding model and get its dimension."""
        if self.embedder is None:
            from sentence_transformers import SentenceTransformer
            import torch
            self.embedder = SentenceTransformer(
                self.embed_model_name, 
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
            # Get embedding dimension
            test_embedding = self.embedder.encode(["test"])
            self.embedding_dimension = len(test_embedding[0])
        return self.embedder
    
    def _connect_shibudb(self):
        """Connect to ShibuDB and set up vector and metadata spaces."""
        try:
            self.client = ShibuDbClient(self.shibudb_host, self.shibudb_port)
            self.client.authenticate("admin", "admin")
            
            # Get embedding dimension first
            embedder = self._get_embedder()
            
            # Create vector space for embeddings
            vector_space_name = f"{self.space_name}_vectors"
            try:
                resp = self.client.create_space(
                    vector_space_name, 
                    "vector", 
                    dimension=self.embedding_dimension,
                    index_type="HNSW32",
                    metric="InnerProduct"
                )
                console.print(f"[green]Created vector space '{vector_space_name}' with dimension {self.embedding_dimension}[/], resp = {resp}")
            except Exception as e:
                console.print(f"[blue]Vector space already exists or error: {e}[/]")
            
            # Create metadata space for chunk and file metadata
            meta_space_name = f"{self.space_name}_meta"
            try:
                resp = self.client.create_space(meta_space_name, "key-value")
                console.print(f"[green]Created metadata space '{meta_space_name}'[/], resp = {resp}")
            except Exception as e:
                console.print(f"[blue]Metadata space already exists or error: {e}[/]")
            
            console.print(f"[green]Connected to ShibuDB at {self.shibudb_host}:{self.shibudb_port}[/]")
            console.print(f"[blue]Using vector space: {vector_space_name}[/]")
            console.print(f"[blue]Using metadata space: {meta_space_name}[/]")
            
        except Exception as e:
            console.print(f"[red]Failed to connect to ShibuDB: {e}[/]")
            console.print("[yellow]Falling back to in-memory indexing[/]")
            self.client = None
    
    def _get_file_hash(self, file_path: pathlib.Path) -> str:
        """Calculate hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _get_file_metadata(self, file_path: pathlib.Path) -> FileMetadata:
        """Get metadata for a file."""
        stat = file_path.stat()
        return FileMetadata(
            path=str(file_path.relative_to(self.repo_root)),
            size=stat.st_size,
            mtime=stat.st_mtime,
            hash=self._get_file_hash(file_path),
            indexed_at=datetime.now().isoformat(),
            chunk_count=0
        )
    
    def _should_index(self, path: pathlib.Path) -> bool:
        """Check if file should be indexed."""
        if any(part in IGNORE_DIRS for part in path.parts):
            return False
        return path.suffix.lower() in CODE_EXTS
    
    def _load_file_metadata(self):
        """Load file metadata from ShibuDB metadata space."""
        if not self.client:
            return
        
        try:
            meta_space_name = f"{self.space_name}_meta"
            
            # Get the list of file paths
            response = self.client.get("file_metadata_list", space=meta_space_name)
            console.print(f"[dim]Debug: file_metadata_list response: {response}[/]")
            
            if response.get("status") == "OK" and "value" in response:
                # Direct response structure - status and value at top level
                file_paths_str = response["value"]
                file_paths = file_paths_str.strip().split('\n') if file_paths_str.strip() else []
                console.print(f"[dim]Debug: Found {len(file_paths)} file paths in metadata[/]")
            else:
                console.print(f"[yellow]No file paths found (status: {response.get('status')}), starting fresh[/]")
                self.file_metadata = {}
                return
                
            # Load each file's metadata individually
            self.file_metadata = {}
            for path in file_paths:
                safe_key = f"file_meta_{path.replace('/', '_').replace('\\', '_')}"
                meta_response = self.client.get(safe_key, space=meta_space_name)
                console.print(f"[dim]Debug: {safe_key} response: {meta_response}[/]")
                
                if meta_response.get("status") == "OK" and "value" in meta_response:
                    # Direct response structure - status and value at top level
                    meta_str = meta_response["value"]
                    parts = meta_str.split('|')
                    if len(parts) == 6:
                        self.file_metadata[path] = FileMetadata(
                            path=parts[0],
                            size=int(parts[1]),
                            mtime=float(parts[2]),
                            hash=parts[3],
                            indexed_at=parts[4],
                            chunk_count=int(parts[5])
                        )
                    else:
                        console.print(f"[yellow]Warning: Invalid metadata format for {path}[/]")
                else:
                    console.print(f"[yellow]Warning: Could not load metadata for {path}[/]")
            
            console.print(f"[blue]Loaded metadata for {len(self.file_metadata)} files[/]")
        except Exception as e:
            console.print(f"[yellow]Could not load file metadata: {e}[/]")
            console.print(f"[dim]Debug: Exception details: {type(e).__name__}: {str(e)}[/]")
            import traceback
            console.print(f"[dim]Debug: Traceback: {traceback.format_exc()}[/]")
            self.file_metadata = {}
    
    def _save_file_metadata(self):
        """Save file metadata to ShibuDB metadata space."""
        if not self.client:
            return
        
        try:
            meta_space_name = f"{self.space_name}_meta"
            
            # Store each file's metadata under its own key
            for path, meta in self.file_metadata.items():
                # Use file path as key (with safe encoding)
                safe_key = f"file_meta_{path.replace('/', '_').replace('\\', '_')}"
                # Store as simple string, not JSON
                meta_str = f"{meta.path}|{meta.size}|{meta.mtime}|{meta.hash}|{meta.indexed_at}|{meta.chunk_count}"
                response = self.client.put(safe_key, meta_str, space=meta_space_name)
                console.print(f"[dim]Debug: Saved {safe_key}, response: {response}[/]")
            
            # Store the list of all file paths as simple newline-separated string
            file_paths = list(self.file_metadata.keys())
            file_paths_str = "\n".join(file_paths)
            response = self.client.put("file_metadata_list", file_paths_str, space=meta_space_name)
            console.print(f"[dim]Debug: Saved file_metadata_list, response: {response}[/]")
            
            console.print(f"[blue]Saved metadata for {len(self.file_metadata)} files[/]")
        except Exception as e:
            console.print(f"[yellow]Could not save file metadata: {e}[/]")
            import traceback
            console.print(f"[dim]Debug: Traceback: {traceback.format_exc()}[/]")
    
    def _get_changed_files(self) -> Tuple[List[pathlib.Path], List[pathlib.Path], List[pathlib.Path]]:
        """Get lists of new, modified, and deleted files."""
        current_files = set()
        new_files = []
        modified_files = []
        
        # Scan current files
        for file_path in pathlib.Path(self.repo_root).rglob("*"):
            if file_path.is_file() and self._should_index(file_path):
                rel_path = str(file_path.relative_to(self.repo_root))
                current_files.add(rel_path)
                
                # Check if file is new or modified
                if rel_path not in self.file_metadata:
                    new_files.append(file_path)
                else:
                    current_meta = self._get_file_metadata(file_path)
                    stored_meta = self.file_metadata[rel_path]
                    
                    if (current_meta.size != stored_meta.size or 
                        current_meta.mtime != stored_meta.mtime or
                        current_meta.hash != stored_meta.hash):
                        modified_files.append(file_path)
        
        # Find deleted files
        deleted_files = [
            pathlib.Path(self.repo_root) / path 
            for path in self.file_metadata.keys() 
            if path not in current_files
        ]
        
        return new_files, modified_files, deleted_files
    
    def _remove_file_from_index(self, file_path: pathlib.Path):
        """Remove file and its chunks from the index."""
        if not self.client:
            return
        
        rel_path = str(file_path.relative_to(self.repo_root))
        meta_space_name = f"{self.space_name}_meta"
        
        # Remove from metadata
        if rel_path in self.file_metadata:
            del self.file_metadata[rel_path]
            
            # Remove file metadata from ShibuDB
            safe_key = f"file_meta_{rel_path.replace('/', '_').replace('\\', '_')}"
            self.client.delete(safe_key, space=meta_space_name)
        
        # Remove chunks from metadata space
        try:
            # Get all vector IDs for this file
            response = self.client.get(f"file_chunks_{rel_path}", space=meta_space_name)
            
            if response.get("status") == "OK" and "value" in response:
                # Direct response structure - status and value at top level
                chunk_ids = json.loads(response["value"])
                console.print(f"[blue]Removing {len(chunk_ids)} chunks for deleted file: {rel_path}[/]")
                
                # Remove chunk metadata
                for chunk_id in chunk_ids:
                    self.client.delete(f"chunk_{chunk_id}", space=meta_space_name)
                
                # Remove file chunks list
                self.client.delete(f"file_chunks_{rel_path}", space=meta_space_name)
                
                console.print(f"[green]Removed chunks for deleted file: {rel_path}[/]")
            else:
                console.print(f"[yellow]No chunks found for deleted file: {rel_path}[/]")
                
        except Exception as e:
            console.print(f"[yellow]Could not remove chunks for {rel_path}: {e}[/]")
    
    def _index_file(self, file_path: pathlib.Path) -> List[Chunk]:
        """Index a single file and return its chunks."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            return []
        
        if not text.strip():
            return []
        
        # Create chunks
        chunks = []
        n = len(text)
        i = 0
        while i < n:
            j = min(i + self.max_chunk_chars, n)
            piece = text[i:j]
            if piece.strip():
                chunk = Chunk(
                    path=str(file_path),
                    start=i,
                    end=j,
                    text=piece
                )
                chunks.append(chunk)
            
            if j >= n:
                break
            i = j - self.overlap
            i = max(i, 0)
            if i >= n:
                break
        
        return chunks
    
    def _store_chunks_in_shibudb(self, chunks: List[Chunk]):
        """Store chunks and their embeddings in ShibuDB using separate vector and metadata spaces."""
        if not self.client or not chunks:
            return
        
        try:
            embedder = self._get_embedder()
            vector_space_name = f"{self.space_name}_vectors"
            meta_space_name = f"{self.space_name}_meta"
            
            # Prepare embeddings (disable progress bar to avoid new lines)
            texts = [self._prep_embed_text(chunk) for chunk in chunks]
            embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            
            # Store each chunk with proper vector ID
            chunk_ids = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Create a unique vector ID
                chunk_hash = hashlib.md5(f"{chunk.path}_{chunk.start}_{chunk.end}".encode()).hexdigest()
                vector_id = int(chunk_hash[:8], 16)  # Use first 8 chars as int
                
                chunk_ids.append(vector_id)
                
                # Store vector in vector space
                response = self.client.insert_vector(vector_id, embedding.tolist(), space=vector_space_name)
                if response.get("status") != "OK":
                    console.print(f"[yellow]Warning: Failed to store vector {vector_id}: {response}[/]")
                
                # Store chunk metadata in metadata space
                chunk_meta = {
                    "path": chunk.path,
                    "start": chunk.start,
                    "end": chunk.end,
                    "text": chunk.text[:1000],  # Truncate for storage
                    "vector_id": vector_id,
                    "chunk_hash": chunk_hash
                }
                self.client.put(f"chunk_{vector_id}", json.dumps(chunk_meta), space=meta_space_name)
            
            # Store chunk IDs for this file in metadata space
            rel_path = str(pathlib.Path(chunks[0].path).relative_to(self.repo_root))
            self.client.put(f"file_chunks_{rel_path}", json.dumps(chunk_ids), space=meta_space_name)
            
        except Exception as e:
            console.print(f"[red]Error storing chunks in ShibuDB: {e}[/]")
            import traceback
            traceback.print_exc()
    
    def _prep_embed_text(self, chunk: Chunk) -> str:
        """Prepare text for embedding."""
        header = f"PATH: {os.path.relpath(chunk.path, self.repo_root)}\nSPAN: {chunk.start}-{chunk.end}\n---\n"
        return header + chunk.text
    
    def build(self, force_rebuild: bool = False):
        """Build or update the index with progress bar."""
        console.print(f"[bold cyan]Building persistent index for:[/] {self.repo_root}")
        
        # Connect to ShibuDB
        self._connect_shibudb()
        
        # Load existing metadata
        self._load_file_metadata()
        
        if force_rebuild:
            console.print("[yellow]Force rebuild requested - clearing existing index[/]")
            self.file_metadata = {}
        
        # Get changed files
        new_files, modified_files, deleted_files = self._get_changed_files()
        
        console.print(f"[blue]Found {len(new_files)} new files, {len(modified_files)} modified files, {len(deleted_files)} deleted files[/]")
        
        # Process deleted files
        for file_path in deleted_files:
            console.print(f"[red]Removing deleted file:[/] {file_path.name}")
            self._remove_file_from_index(file_path)
        
        # Process new and modified files
        files_to_process = new_files + modified_files
        if not files_to_process:
            console.print("[green]No changes detected - index is up to date![/]")
            return
        
        # Create progress bar
        with Progress(
            TextColumn("[bold blue]Indexing files"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            TextColumn("[bold green]{task.completed}/{task.total} files"),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
            expand=True
        ) as progress:
            
            # Create main task
            task = progress.add_task(
                f"Processing {len(files_to_process)} files...", 
                total=len(files_to_process)
            )
            
            total_chunks = 0
            for i, file_path in enumerate(files_to_process):
                # Update progress description with current file
                rel_path = str(file_path.relative_to(self.repo_root))
                progress.update(
                    task, 
                    description=f"[cyan]Processing:[/] {rel_path}",
                    advance=1
                )
                
                # Index the file
                chunks = self._index_file(file_path)
                if chunks:
                    # Store in ShibuDB
                    self._store_chunks_in_shibudb(chunks)
                    
                    # Update metadata
                    meta = self._get_file_metadata(file_path)
                    meta.chunk_count = len(chunks)
                    self.file_metadata[rel_path] = meta
                    
                    total_chunks += len(chunks)
        
        # Save updated metadata
        self._save_file_metadata()
        
        console.print(f"[green]✅ Index updated successfully![/] Processed {len(files_to_process)} files, {total_chunks} chunks")
    
    def retrieve(self, query: str, top_k: int = 12) -> List[Chunk]:
        """Retrieve relevant chunks using ShibuDB vector search."""
        if not self.client:
            console.print("[red]ShibuDB not connected - cannot retrieve[/]")
            return []
        
        try:
            embedder = self._get_embedder()
            vector_space_name = f"{self.space_name}_vectors"
            meta_space_name = f"{self.space_name}_meta"
            
            # Encode query
            query_embedding = embedder.encode([query], normalize_embeddings=True)[0]
            
            # Search in ShibuDB vector space
            response = self.client.search_topk(query_embedding.tolist(), k=top_k, space=vector_space_name)
            console.print(query_embedding.tolist())
            console.print(response)
            
            if response.get("status") != "OK":
                console.print(f"[red]Vector search failed: {response}[/]")
                return []
            
            # Direct response structure - status and results at top level
            if response.get("status") == "OK" and "message" in response:
                results = json.loads(response["message"], strict=False)
            else:
                console.print(f"[red]No results found in response[/]")
                return []
            
            console.print(f"[blue]Found {len(results)} similar vectors[/]")
            
            # Reconstruct chunks from vector search results
            chunks = []
            for result in results:
                vector_id = result.get("id")
                distance = result.get("distance", 0)
                
                if vector_id:
                    # Get chunk metadata from metadata space
                    chunk_meta_response = self.client.get(f"chunk_{vector_id}", space=meta_space_name)
                    
                    if chunk_meta_response.get("status") == "OK" and "value" in chunk_meta_response:
                        # Direct response structure - status and value at top level
                        chunk_meta = json.loads(chunk_meta_response["value"])
                        
                        chunk = Chunk(
                            path=chunk_meta["path"],
                            start=chunk_meta["start"],
                            end=chunk_meta["end"],
                            text=chunk_meta["text"]
                        )
                        chunks.append(chunk)
                        console.print(f"[dim]Retrieved chunk from {chunk.path} (distance: {distance:.4f})[/]")
                    else:
                        console.print(f"[yellow]Warning: Could not retrieve metadata for vector {vector_id}[/]")
            
            console.print(f"[green]Retrieved {len(chunks)} chunks from ShibuDB (vectors from {vector_space_name}, metadata from {meta_space_name})[/]")
            return chunks
            
        except Exception as e:
            console.print(f"[red]Error retrieving from ShibuDB: {e}[/]")
            import traceback
            traceback.print_exc()
            return []
    
    def get_stats(self) -> Dict[str, any]:
        """Get indexing statistics."""
        return {
            "total_files": len(self.file_metadata),
            "total_chunks": sum(meta.chunk_count for meta in self.file_metadata.values()),
            "repo_root": self.repo_root,
            "space_name": self.space_name,
            "vector_space": f"{self.space_name}_vectors",
            "metadata_space": f"{self.space_name}_meta",
            "shibudb_connected": self.client is not None,
            "embedding_dimension": self.embedding_dimension,
            "indexer_type": "shibudb_two_spaces"
        }
