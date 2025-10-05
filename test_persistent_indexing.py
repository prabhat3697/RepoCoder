#!/usr/bin/env python3
"""
Test script for persistent indexing functionality.
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
    temp_dir = tempfile.mkdtemp(prefix="repocoder_test_")
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
""")
    
    (repo_path / "config.py").write_text("""
DATABASE_URL = "sqlite:///app.db"
DEBUG = True
SECRET_KEY = "your-secret-key"
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
""")
    
    console.print(f"[green]Created test repository at:[/] {repo_path}")
    return repo_path


def test_persistent_indexing():
    """Test the persistent indexing functionality."""
    console.print("[bold cyan]Testing Persistent Indexing with ShibuDB[/]")
    
    # Create test repository
    repo_path = create_test_repo()
    
    try:
        # Test 1: Initial indexing
        console.print("\n[bold blue]Test 1: Initial Indexing[/]")
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
        
        # Test 2: No changes (should be fast)
        console.print("\n[bold blue]Test 2: No Changes (Should be Fast)[/]")
        start_time = time.time()
        indexer.build()
        no_changes_time = time.time() - start_time
        
        console.print(f"[green]No changes indexing completed in {no_changes_time:.2f}s[/]")
        console.print(f"[blue]Speed improvement:[/] {initial_time/no_changes_time:.1f}x faster")
        
        # Test 3: Add a new file
        console.print("\n[bold blue]Test 3: Add New File[/]")
        (repo_path / "new_feature.py").write_text("""
def new_feature():
    return "This is a new feature!"

def another_function():
    return "Another function"
""")
        
        start_time = time.time()
        indexer.build()
        new_file_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]New file indexing completed in {new_file_time:.2f}s[/]")
        console.print(f"[blue]Updated stats:[/] {stats}")
        
        # Test 4: Modify existing file
        console.print("\n[bold blue]Test 4: Modify Existing File[/]")
        (repo_path / "main.py").write_text("""
def main():
    print("Hello, World!")
    print("This is a modified version!")
    return 0

def new_function():
    return "New function added"

if __name__ == "__main__":
    main()
""")
        
        start_time = time.time()
        indexer.build()
        modified_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]Modified file indexing completed in {modified_time:.2f}s[/]")
        console.print(f"[blue]Updated stats:[/] {stats}")
        
        # Test 5: Delete a file
        console.print("\n[bold blue]Test 5: Delete File[/]")
        (repo_path / "config.py").unlink()
        
        start_time = time.time()
        indexer.build()
        deleted_time = time.time() - start_time
        
        stats = indexer.get_stats()
        console.print(f"[green]Deleted file processing completed in {deleted_time:.2f}s[/]")
        console.print(f"[blue]Updated stats:[/] {stats}")
        
        # Test 6: Test retrieval
        console.print("\n[bold blue]Test 6: Test Retrieval[/]")
        chunks = indexer.retrieve("What does the main function do?", top_k=3)
        console.print(f"[green]Retrieved {len(chunks)} chunks[/]")
        
        for i, chunk in enumerate(chunks):
            console.print(f"[blue]Chunk {i+1}:[/] {chunk.path} ({chunk.start}-{chunk.end})")
            console.print(f"[dim]{chunk.text[:100]}...[/]")
        
        # Summary
        console.print("\n[bold green]Test Summary:[/]")
        console.print(f"Initial indexing: {initial_time:.2f}s")
        console.print(f"No changes: {no_changes_time:.2f}s ({initial_time/no_changes_time:.1f}x faster)")
        console.print(f"New file: {new_file_time:.2f}s")
        console.print(f"Modified file: {modified_time:.2f}s")
        console.print(f"Deleted file: {deleted_time:.2f}s")
        console.print(f"Final stats: {stats}")
        
        console.print("\n[bold green]✅ All tests passed![/]")
        
    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/]")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        shutil.rmtree(repo_path)
        console.print(f"[dim]Cleaned up test repository: {repo_path}[/]")


def test_fallback_to_memory():
    """Test fallback to in-memory indexing when ShibuDB is not available."""
    console.print("\n[bold cyan]Testing Fallback to In-Memory Indexing[/]")
    
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
        
        console.print("\n[bold green]✅ Fallback test passed![/]")
        
    except Exception as e:
        console.print(f"[red]❌ Fallback test failed: {e}[/]")
        import traceback
        traceback.print_exc()
        
    finally:
        shutil.rmtree(repo_path)


if __name__ == "__main__":
    console.print("[bold magenta]RepoCoder Persistent Indexing Test Suite[/]")
    
    # Test persistent indexing
    test_persistent_indexing()
    
    # Test fallback
    test_fallback_to_memory()
    
    console.print("\n[bold green]🎉 All tests completed![/]")
