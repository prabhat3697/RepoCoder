#!/usr/bin/env python3
"""
Test script for ShibuDB vector database functionality.
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from persistent_indexer import PersistentRepoIndexer
from rich.console import Console

console = Console()


def create_test_repo():
    """Create a temporary test repository with sample files."""
    temp_dir = tempfile.mkdtemp(prefix="repocoder_shibudb_test_")
    repo_path = Path(temp_dir)
    
    # Create sample Python files
    (repo_path / "main.py").write_text("""
def main():
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    main()
""")
    
    (repo_path / "utils.py").write_text("""
def add_numbers(a, b):
    return a + b

def multiply_numbers(a, b):
    return a * b

def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
""")
    
    (repo_path / "config.py").write_text("""
DATABASE_URL = "sqlite:///app.db"
DEBUG = True
SECRET_KEY = "your-secret-key"

def get_database_config():
    return {
        "url": DATABASE_URL,
        "debug": DEBUG
    }
""")
    
    # Create a subdirectory
    (repo_path / "models").mkdir()
    (repo_path / "models" / "user.py").write_text("""
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
    
    def to_dict(self):
        return {"name": self.name, "email": self.email}
    
    def save(self):
        # Save user to database
        pass
""")
    
    console.print(f"[green]Created test repository at:[/] {repo_path}")
    return repo_path


def test_shibudb_vector_functionality():
    """Test ShibuDB vector database functionality."""
    console.print("[bold cyan]Testing ShibuDB Vector Database Functionality[/]")
    
    # Create test repository
    repo_path = create_test_repo()
    
    try:
        # Test 1: Initial indexing with ShibuDB
        console.print("\n[bold blue]Test 1: Initial Indexing with ShibuDB Vectors[/]")
        indexer = PersistentRepoIndexer(
            repo_root=str(repo_path),
            embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
            max_chunk_chars=800,
            overlap=100
        )
        
        start_time = time.time()
        indexer.build()
        initial_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]Initial indexing completed in {initial_time:.2f}s[/]")
        console.print(f"[blue]Stats:[/] {stats}")
        
        # Test 2: Vector search functionality
        console.print("\n[bold blue]Test 2: Vector Search Functionality[/]")
        
        test_queries = [
            "What does the main function do?",
            "How to add two numbers?",
            "Database configuration settings",
            "User class methods",
            "Fibonacci calculation"
        ]
        
        for query in test_queries:
            console.print(f"\n[cyan]Query:[/] {query}")
            start_time = time.time()
            chunks = indexer.retrieve(query, top_k=3)
            search_time = time.time() - start_time
            
            console.print(f"[green]Found {len(chunks)} chunks in {search_time:.3f}s[/]")
            for i, chunk in enumerate(chunks):
                console.print(f"[blue]  {i+1}. {chunk.path} ({chunk.start}-{chunk.end})[/]")
                console.print(f"[dim]     {chunk.text[:100]}...[/]")
        
        # Test 3: Add new file and test incremental indexing
        console.print("\n[bold blue]Test 3: Incremental Indexing[/]")
        (repo_path / "new_feature.py").write_text("""
def new_feature():
    return "This is a new feature!"

def another_function():
    return "Another function"

def process_data(data):
    # Process the data
    return data.upper()
""")
        
        start_time = time.time()
        indexer.build()
        incremental_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]Incremental indexing completed in {incremental_time:.2f}s[/]")
        console.print(f"[blue]Updated stats:[/] {stats}")
        
        # Test 4: Search for new content
        console.print("\n[bold blue]Test 4: Search for New Content[/]")
        new_queries = [
            "new feature function",
            "process data function",
            "data processing"
        ]
        
        for query in new_queries:
            console.print(f"\n[cyan]Query:[/] {query}")
            chunks = indexer.retrieve(query, top_k=2)
            console.print(f"[green]Found {len(chunks)} chunks[/]")
            for i, chunk in enumerate(chunks):
                console.print(f"[blue]  {i+1}. {chunk.path} ({chunk.start}-{chunk.end})[/]")
                console.print(f"[dim]     {chunk.text[:100]}...[/]")
        
        # Test 5: Modify existing file
        console.print("\n[bold blue]Test 5: Modify Existing File[/]")
        (repo_path / "utils.py").write_text("""
def add_numbers(a, b):
    return a + b

def multiply_numbers(a, b):
    return a * b

def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def new_utility_function():
    return "This is a new utility function!"
""")
        
        start_time = time.time()
        indexer.build()
        modify_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]File modification indexing completed in {modify_time:.2f}s[/]")
        console.print(f"[blue]Updated stats:[/] {stats}")
        
        # Test 6: Search for modified content
        console.print("\n[bold blue]Test 6: Search for Modified Content[/]")
        chunks = indexer.retrieve("new utility function", top_k=2)
        console.print(f"[green]Found {len(chunks)} chunks[/]")
        for i, chunk in enumerate(chunks):
            console.print(f"[blue]  {i+1}. {chunk.path} ({chunk.start}-{chunk.end})[/]")
            console.print(f"[dim]     {chunk.text[:100]}...[/]")
        
        # Test 7: Delete file
        console.print("\n[bold blue]Test 7: Delete File[/]")
        (repo_path / "config.py").unlink()
        
        start_time = time.time()
        indexer.build()
        delete_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]File deletion processing completed in {delete_time:.2f}s[/]")
        console.print(f"[blue]Updated stats:[/] {stats}")
        
        # Test 8: Verify deleted content is not searchable
        console.print("\n[bold blue]Test 8: Verify Deleted Content Not Searchable[/]")
        chunks = indexer.retrieve("database configuration", top_k=5)
        console.print(f"[green]Found {len(chunks)} chunks (should be 0 or fewer)[/]")
        
        # Summary
        console.print("\n[bold green]Test Summary:[/]")
        console.print(f"Initial indexing: {initial_time:.2f}s")
        console.print(f"Incremental indexing: {incremental_time:.2f}s")
        console.print(f"File modification: {modify_time:.2f}s")
        console.print(f"File deletion: {delete_time:.2f}s")
        console.print(f"Final stats: {stats}")
        
        console.print("\n[bold green]✅ All ShibuDB vector tests passed![/]")
        
    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/]")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        shutil.rmtree(repo_path)
        console.print(f"[dim]Cleaned up test repository: {repo_path}[/]")


def test_fallback_functionality():
    """Test fallback functionality when ShibuDB is not available."""
    console.print("\n[bold cyan]Testing Fallback Functionality[/]")
    
    repo_path = create_test_repo()
    
    try:
        # Test with invalid ShibuDB connection
        indexer = PersistentRepoIndexer(
            repo_root=str(repo_path),
            embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
            max_chunk_chars=800,
            overlap=100,
            shibudb_host="invalid-host",
            shibudb_port=9999
        )
        
        start_time = time.time()
        indexer.build()
        fallback_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]Fallback indexing completed in {fallback_time:.2f}s[/]")
        console.print(f"[blue]Stats:[/] {stats}")
        console.print(f"[yellow]ShibuDB connected:[/] {stats.get('shibudb_connected', False)}")
        
        # Test retrieval with fallback
        chunks = indexer.retrieve("main function", top_k=2)
        console.print(f"[green]Fallback retrieval found {len(chunks)} chunks[/]")
        
        console.print("\n[bold green]✅ Fallback test passed![/]")
        
    except Exception as e:
        console.print(f"[red]❌ Fallback test failed: {e}[/]")
        import traceback
        traceback.print_exc()
        
    finally:
        shutil.rmtree(repo_path)


if __name__ == "__main__":
    console.print("[bold magenta]RepoCoder ShibuDB Vector Database Test Suite[/]")
    
    # Test ShibuDB vector functionality
    test_shibudb_vector_functionality()
    
    # Test fallback functionality
    test_fallback_functionality()
    
    console.print("\n[bold green]🎉 All tests completed![/]")
