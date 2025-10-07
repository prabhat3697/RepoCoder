#!/usr/bin/env python3
"""
Test script for the new intelligent query routing system.
"""

import requests
import json
from rich.console import Console
from rich.table import Table

console = Console()

def test_query_routing():
    """Test different types of queries to see routing in action."""
    
    base_url = "http://localhost:8000"
    
    # Test queries of different types
    test_queries = [
        {
            "prompt": "How many files are there in my project?",
            "expected_type": "general_info",
            "description": "General information query"
        },
        {
            "prompt": "Explain how the indexer works in this codebase",
            "expected_type": "code_analysis", 
            "description": "Code analysis query"
        },
        {
            "prompt": "Add a new function to validate user input",
            "expected_type": "code_generation",
            "description": "Code generation query"
        },
        {
            "prompt": "Find all functions that handle file operations",
            "expected_type": "search",
            "description": "Search query"
        },
        {
            "prompt": "Why is my code failing with an error?",
            "expected_type": "debugging",
            "description": "Debugging query"
        },
        {
            "prompt": "Write unit tests for the query router",
            "expected_type": "testing",
            "description": "Testing query"
        }
    ]
    
    console.print("[bold cyan]Testing Intelligent Query Routing System[/]")
    console.print("=" * 60)
    
    # Create results table
    table = Table(title="Query Routing Results")
    table.add_column("Query Type", style="cyan")
    table.add_column("Selected Model", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Response Time", style="blue")
    table.add_column("Status", style="red")
    
    for i, test in enumerate(test_queries, 1):
        console.print(f"\n[bold blue]Test {i}:[/] {test['description']}")
        console.print(f"[dim]Query:[/] {test['prompt']}")
        
        try:
            response = requests.post(
                f"{base_url}/query",
                json={
                    "prompt": test["prompt"],
                    "top_k": 8,
                    "max_new_tokens": 200,
                    "temperature": 0.2
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})
                routing = result.get("routing", {})
                
                selected_model = routing.get("selected_model", "unknown")
                confidence = routing.get("confidence", 0.0)
                query_type = routing.get("query_type", "unknown")
                took_ms = data.get("took_ms", 0)
                
                # Check if routing worked as expected
                status = "✅" if query_type == test["expected_type"] else "⚠️"
                
                table.add_row(
                    query_type,
                    selected_model,
                    f"{confidence:.2f}",
                    f"{took_ms}ms",
                    status
                )
                
                console.print(f"[green]✅ Success[/] - Routed to {selected_model} ({query_type})")
                console.print(f"[dim]Response preview:[/] {result.get('analysis', '')[:100]}...")
                
            else:
                table.add_row(
                    test["expected_type"],
                    "ERROR",
                    "0.00",
                    "0ms",
                    "❌"
                )
                console.print(f"[red]❌ Error {response.status_code}:[/] {response.text}")
                
        except Exception as e:
            table.add_row(
                test["expected_type"],
                "ERROR",
                "0.00",
                "0ms",
                "❌"
            )
            console.print(f"[red]❌ Exception:[/] {e}")
    
    console.print("\n")
    console.print(table)
    
    # Test stats endpoint
    console.print("\n[bold cyan]System Stats:[/]")
    try:
        stats_response = requests.get(f"{base_url}/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            console.print(f"[blue]Total files indexed:[/] {stats.get('total_files', 0)}")
            console.print(f"[blue]Total chunks:[/] {stats.get('total_chunks', 0)}")
            console.print(f"[blue]Repository:[/] {stats.get('repo_root', 'unknown')}")
            console.print(f"[blue]ShibuDB connected:[/] {stats.get('shibudb_connected', False)}")
        else:
            console.print(f"[red]Could not get stats:[/] {stats_response.status_code}")
    except Exception as e:
        console.print(f"[red]Stats error:[/] {e}")

if __name__ == "__main__":
    test_query_routing()
