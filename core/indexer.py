"""
Core Indexer - Minimal implementation
Handles file tree building, chunking, and vector storage
"""

import os
import hashlib
import pathlib
from typing import List, Dict, Set, Optional
from dataclasses import asdict
from rich.console import Console

from .types import FileNode, CodeChunk

console = Console()


class CoreIndexer:
    """
    Minimal core indexer that:
    1. Builds file tree
    2. Extracts code chunks
    3. Stores in vector DB
    4. Tracks metadata
    """
    
    def __init__(self, repo_root: str, code_extensions: Set[str], ignore_dirs: Set[str]):
        self.repo_root = pathlib.Path(repo_root).resolve()
        self.code_extensions = code_extensions
        self.ignore_dirs = ignore_dirs
        
        # Storage
        self.file_tree: List[FileNode] = []
        self.chunks: List[CodeChunk] = []
        self.file_index: Dict[str, FileNode] = {}
        
        console.print(f"[blue]Initializing CoreIndexer for:[/] {self.repo_root}")
    
    def build_file_tree(self) -> List[FileNode]:
        """Build file tree from repository"""
        console.print("[cyan]Building file tree...[/]")
        
        self.file_tree = []
        self.file_index = {}
        
        for file_path in self.repo_root.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Check if should be ignored
            if self._should_ignore(file_path):
                continue
            
            # Create file node
            file_node = self._create_file_node(file_path)
            self.file_tree.append(file_node)
            self.file_index[str(file_path)] = file_node
        
        console.print(f"[green]Built file tree: {len(self.file_tree)} files[/]")
        return self.file_tree
    
    def extract_chunks(self, chunk_size: int = 1600, overlap: int = 200) -> List[CodeChunk]:
        """Extract code chunks from files"""
        console.print("[cyan]Extracting code chunks...[/]")
        
        self.chunks = []
        chunk_id = 0
        
        for file_node in self.file_tree:
            if not file_node.is_code:
                continue
            
            # Read file content
            try:
                with open(file_node.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                console.print(f"[yellow]Warning: Could not read {file_node.name}: {e}[/]")
                continue
            
            # Split into chunks
            file_chunks = self._chunk_text(
                content, 
                file_node.path, 
                file_node.language or "text",
                chunk_size, 
                overlap
            )
            
            # Assign IDs
            for chunk in file_chunks:
                chunk.id = f"chunk_{chunk_id}"
                chunk_id += 1
                self.chunks.append(chunk)
        
        console.print(f"[green]Extracted {len(self.chunks)} code chunks[/]")
        return self.chunks
    
    def _should_ignore(self, file_path: pathlib.Path) -> bool:
        """Check if file should be ignored"""
        # Check ignore directories
        for part in file_path.parts:
            if part in self.ignore_dirs:
                return True
        
        # Check if it's a code file
        if file_path.suffix.lower() not in self.code_extensions:
            return True
        
        return False
    
    def _create_file_node(self, file_path: pathlib.Path) -> FileNode:
        """Create a FileNode from a file path"""
        rel_path = str(file_path.relative_to(self.repo_root))
        extension = file_path.suffix.lower()
        size = file_path.stat().st_size
        
        # Detect language
        language = self._detect_language(extension)
        
        return FileNode(
            path=str(file_path),
            name=file_path.name,
            extension=extension,
            size=size,
            language=language,
            is_code=extension in self.code_extensions
        )
    
    def _detect_language(self, extension: str) -> Optional[str]:
        """Detect programming language from extension"""
        language_map = {
            '.py': 'python', '.pyi': 'python',
            '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.c': 'c', '.h': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'shell', '.bash': 'shell',
            '.sql': 'sql',
            '.html': 'html', '.htm': 'html',
            '.css': 'css', '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml', '.yml': 'yaml',
            '.xml': 'xml',
            '.md': 'markdown',
        }
        return language_map.get(extension)
    
    def _chunk_text(self, text: str, file_path: str, language: str, 
                    chunk_size: int, overlap: int) -> List[CodeChunk]:
        """Split text into overlapping chunks"""
        chunks = []
        lines = text.split('\n')
        total_lines = len(lines)
        
        # Calculate chunks by character count
        current_chunk = []
        current_size = 0
        start_line = 0
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > chunk_size and current_chunk:
                # Save current chunk
                chunk_content = '\n'.join(current_chunk)
                chunks.append(CodeChunk(
                    id="",  # Will be assigned later
                    file_path=file_path,
                    start_line=start_line,
                    end_line=i,
                    content=chunk_content,
                    language=language,
                    metadata={'file_size': len(text)}
                ))
                
                # Start new chunk with overlap
                overlap_lines = max(1, overlap // 50)  # Approximate lines for overlap
                current_chunk = current_chunk[-overlap_lines:] if len(current_chunk) > overlap_lines else []
                current_size = sum(len(l) + 1 for l in current_chunk)
                start_line = i - len(current_chunk)
            
            current_chunk.append(line)
            current_size += line_size
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            chunks.append(CodeChunk(
                id="",
                file_path=file_path,
                start_line=start_line,
                end_line=total_lines,
                content=chunk_content,
                language=language,
                metadata={'file_size': len(text)}
            ))
        
        return chunks
    
    def get_file_by_name(self, filename: str) -> Optional[FileNode]:
        """Get file node by filename"""
        filename_lower = filename.lower()
        
        for file_node in self.file_tree:
            if file_node.name.lower() == filename_lower:
                return file_node
            if filename_lower in file_node.path.lower():
                return file_node
        
        return None
    
    def get_chunks_by_file(self, file_path: str) -> List[CodeChunk]:
        """Get all chunks from a specific file"""
        return [chunk for chunk in self.chunks if chunk.file_path == file_path]
    
    def get_stats(self) -> Dict[str, int]:
        """Get indexer statistics"""
        return {
            "total_files": len(self.file_tree),
            "code_files": len([f for f in self.file_tree if f.is_code]),
            "total_chunks": len(self.chunks),
            "languages": len(set(f.language for f in self.file_tree if f.language))
        }

