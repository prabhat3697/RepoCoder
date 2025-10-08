"""
Context Retriever - Retrieves relevant context for queries
Supports multiple retrieval strategies
"""

from typing import List, Optional
import numpy as np
from rich.console import Console

from .types import CodeChunk, FileNode, QueryAnalysis, RetrievalContext
from .indexer import CoreIndexer

console = Console()


class ContextRetriever:
    """
    Retrieves relevant context using different strategies:
    1. File-specific retrieval
    2. Semantic search
    3. Hybrid retrieval
    """
    
    def __init__(self, indexer: CoreIndexer, embedder=None):
        self.indexer = indexer
        self.embedder = embedder
        self.chunk_embeddings: List[np.ndarray] = []
    
    def compute_embeddings(self):
        """Compute embeddings for all chunks"""
        if not self.embedder:
            console.print("[yellow]No embedder provided, skipping embedding computation[/]")
            return
        
        console.print("[cyan]Computing embeddings for chunks...[/]")
        
        # Prepare texts for embedding
        texts = []
        for chunk in self.indexer.chunks:
            # Enhanced text with file context
            file_node = self.indexer.file_index.get(chunk.file_path)
            filename = file_node.name if file_node else "unknown"
            
            text = f"FILE: {filename}\nLANGUAGE: {chunk.language}\n---\n{chunk.content}"
            texts.append(text)
        
        # Compute embeddings
        embeddings = self.embedder.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        self.chunk_embeddings = [emb for emb in embeddings]
        
        # Store embeddings in chunks
        for chunk, embedding in zip(self.indexer.chunks, self.chunk_embeddings):
            chunk.embedding = embedding.tolist()
        
        console.print(f"[green]Computed embeddings for {len(self.chunk_embeddings)} chunks[/]")
    
    def retrieve(self, query_analysis: QueryAnalysis, top_k: int = 20) -> RetrievalContext:
        """Retrieve relevant context based on query analysis"""
        console.print(f"[cyan]Retrieving context for query (top_k={top_k})...[/]")
        
        # Choose strategy based on query analysis
        if query_analysis.file_references:
            # File-specific retrieval
            chunks = self._retrieve_by_files(query_analysis.file_references, top_k)
            strategy = "file_specific"
        elif self.chunk_embeddings:
            # Semantic retrieval
            chunks = self._retrieve_semantic(query_analysis.original_query, top_k)
            strategy = "semantic"
        else:
            # Fallback: return first chunks
            chunks = self.indexer.chunks[:top_k]
            strategy = "fallback"
        
        # Get relevant file tree nodes
        file_paths = list(set(chunk.file_path for chunk in chunks))
        file_tree = [self.indexer.file_index[path] for path in file_paths if path in self.indexer.file_index]
        
        context = RetrievalContext(
            chunks=chunks,
            file_tree=file_tree,
            total_chunks=len(chunks),
            strategy_used=strategy,
            metadata={
                "files_involved": len(file_tree),
                "query_intent": query_analysis.intent.value
            }
        )
        
        console.print(f"[green]Retrieved {len(chunks)} chunks from {len(file_tree)} files using {strategy} strategy[/]")
        return context
    
    def _retrieve_by_files(self, file_refs: List, top_k: int) -> List[CodeChunk]:
        """Retrieve chunks from specific files"""
        chunks = []
        
        for file_ref in file_refs:
            # Find the file
            file_node = self.indexer.get_file_by_name(file_ref.filename)
            if not file_node:
                console.print(f"[yellow]File not found: {file_ref.filename}[/]")
                continue
            
            # Get chunks from this file
            file_chunks = self.indexer.get_chunks_by_file(file_node.path)
            chunks.extend(file_chunks)
        
        # Limit to top_k
        return chunks[:top_k]
    
    def _retrieve_semantic(self, query: str, top_k: int) -> List[CodeChunk]:
        """Retrieve chunks using semantic similarity"""
        if not self.embedder or not self.chunk_embeddings:
            console.print("[yellow]No embeddings available, using fallback[/]")
            return self.indexer.chunks[:top_k]
        
        # Encode query
        query_embedding = self.embedder.encode([query], normalize_embeddings=True)[0]
        
        # Calculate similarities
        similarities = []
        for i, chunk_emb in enumerate(self.chunk_embeddings):
            similarity = np.dot(query_embedding, chunk_emb)
            similarities.append((similarity, i))
        
        # Sort by similarity
        similarities.sort(reverse=True, key=lambda x: x[0])
        
        # Get top_k chunks
        top_indices = [idx for _, idx in similarities[:top_k]]
        chunks = [self.indexer.chunks[idx] for idx in top_indices]
        
        return chunks
    
    def retrieve_hybrid(self, query_analysis: QueryAnalysis, top_k: int = 20, 
                       file_boost: float = 3.0) -> RetrievalContext:
        """Hybrid retrieval combining file-specific and semantic search"""
        if not query_analysis.file_references or not self.chunk_embeddings:
            return self.retrieve(query_analysis, top_k)
        
        console.print("[cyan]Using hybrid retrieval strategy...[/]")
        
        # Encode query
        query_embedding = self.embedder.encode([query_analysis.original_query], normalize_embeddings=True)[0]
        
        # Calculate similarities with file boosting
        similarities = []
        target_files = set(ref.filename.lower() for ref in query_analysis.file_references)
        
        for i, chunk in enumerate(self.indexer.chunks):
            chunk_emb = self.chunk_embeddings[i]
            similarity = np.dot(query_embedding, chunk_emb)
            
            # Boost if chunk is from referenced file
            file_node = self.indexer.file_index.get(chunk.file_path)
            if file_node and file_node.name.lower() in target_files:
                similarity *= file_boost
            
            similarities.append((similarity, i))
        
        # Sort and get top_k
        similarities.sort(reverse=True, key=lambda x: x[0])
        top_indices = [idx for _, idx in similarities[:top_k]]
        chunks = [self.indexer.chunks[idx] for idx in top_indices]
        
        # Get file tree
        file_paths = list(set(chunk.file_path for chunk in chunks))
        file_tree = [self.indexer.file_index[path] for path in file_paths if path in self.indexer.file_index]
        
        context = RetrievalContext(
            chunks=chunks,
            file_tree=file_tree,
            total_chunks=len(chunks),
            strategy_used="hybrid",
            metadata={
                "file_boost_factor": file_boost,
                "files_involved": len(file_tree)
            }
        )
        
        console.print(f"[green]Hybrid retrieval: {len(chunks)} chunks from {len(file_tree)} files[/]")
        return context

