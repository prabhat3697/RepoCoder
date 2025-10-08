#!/usr/bin/env python3
"""
Cursor-style file detection and query preprocessing.
Detects file references in queries and extracts relevant file paths.
"""

import re
import os
import pathlib
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class FileReference:
    """Represents a file reference found in a query."""
    filename: str
    full_path: Optional[str] = None
    confidence: float = 0.0
    context: str = ""
    line_number: Optional[int] = None


@dataclass
class QueryAnalysis:
    """Analysis of a query with file references."""
    original_query: str
    file_references: List[FileReference]
    modified_query: str
    has_file_references: bool = False
    query_type: str = "general"


class CursorStyleFileDetector:
    """Cursor-style file detection system."""
    
    def __init__(self, repo_root: str):
        self.repo_root = pathlib.Path(repo_root).resolve()
        self.file_cache: Dict[str, str] = {}
        self._build_file_index()
    
    def _build_file_index(self):
        """Build an index of all files in the repository."""
        console.print(f"[blue]Building file index for:[/] {self.repo_root}")
        
        # Common code file extensions
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.clj',
            '.hs', '.ml', '.fs', '.r', '.m', '.mm', '.cu', '.cuh', '.cuda',
            '.sql', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
            '.yml', '.yaml', '.json', '.xml', '.toml', '.ini', '.cfg', '.conf',
            '.md', '.rst', '.txt', '.log', '.lock', '.lockb', '.pb', '.proto',
            '.vue', '.svelte', '.astro', '.elm', '.dart', '.lua', '.vim',
            '.css', '.scss', '.sass', '.less', '.styl', '.html', '.htm',
            '.dockerfile', '.dockerignore', '.gitignore', '.gitattributes',
            '.env', '.env.example', '.env.local', '.env.production'
        }
        
        # Ignore common directories
        ignore_dirs = {
            '.git', '.svn', '.hg', 'node_modules', '__pycache__', '.pytest_cache',
            'dist', 'build', '.next', '.nuxt', '.cache', 'coverage', '.coverage',
            'venv', 'env', '.venv', '.env', 'vendor', 'target', 'bin', 'obj',
            '.idea', '.vscode', '.vs', '*.egg-info', '.tox', '.mypy_cache'
        }
        
        for file_path in self.repo_root.rglob("*"):
            if file_path.is_file():
                # Skip ignored directories
                if any(ignore_dir in str(file_path) for ignore_dir in ignore_dirs):
                    continue
                
                # Only index code files
                if file_path.suffix.lower() in code_extensions or file_path.name in {
                    'Dockerfile', 'docker-compose.yml', 'Makefile', 'Rakefile',
                    'Gemfile', 'package.json', 'requirements.txt', 'Pipfile',
                    'Cargo.toml', 'go.mod', 'composer.json', 'pom.xml',
                    'build.gradle', 'CMakeLists.txt', 'meson.build'
                }:
                    rel_path = file_path.relative_to(self.repo_root)
                    self.file_cache[str(rel_path)] = str(file_path)
                    self.file_cache[file_path.name] = str(file_path)
        
        console.print(f"[green]Indexed {len(self.file_cache)} files[/]")
    
    def detect_files_in_query(self, query: str) -> QueryAnalysis:
        """Detect file references in a query (Cursor-style)."""
        file_references = []
        
        # Pattern 1: Direct file references with extensions
        # "How does deploy.rb work?", "Explain app.py", "What's in config.yml?"
        direct_patterns = [
            r'\b(\w+\.\w{2,4})\b',  # filename.ext
            r'["\']([^"\']+\.\w{2,4})["\']',  # "filename.ext"
            r'`([^`]+\.\w{2,4})`',  # `filename.ext`
        ]
        
        # Pattern 2: Path-like references
        # "How does src/utils/helper.py work?", "What's in config/database.yml?"
        path_patterns = [
            r'\b([a-zA-Z0-9_\-/]+\.\w{2,4})\b',  # path/filename.ext
            r'["\']([^"\']*[a-zA-Z0-9_\-/]+\.\w{2,4})["\']',  # "path/filename.ext"
        ]
        
        # Pattern 3: Common file patterns
        # "deploy script", "config file", "package.json", "Dockerfile"
        common_patterns = [
            r'\b(deploy\s*(?:script|file|config)?)\b',
            r'\b(config\s*(?:file|script|yml|yaml|json)?)\b',
            r'\b(package\.json|Dockerfile|Makefile|Rakefile|Gemfile)\b',
            r'\b(requirements\.txt|Pipfile|go\.mod|Cargo\.toml)\b',
            r'\b(build\.gradle|CMakeLists\.txt|meson\.build)\b',
        ]
        
        # Pattern 4: Line number references
        # "line 42 in app.py", "app.py:42", "deploy.rb line 15"
        line_patterns = [
            r'(\w+\.\w{2,4}):(\d+)',  # filename.ext:line
            r'(\w+\.\w{2,4})\s+line\s+(\d+)',  # filename.ext line number
            r'line\s+(\d+)\s+in\s+(\w+\.\w{2,4})',  # line number in filename.ext
        ]
        
        query_lower = query.lower()
        
        # Check line number patterns first
        for pattern in line_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                if len(match.groups()) == 2:
                    if pattern == line_patterns[2]:  # line X in file
                        line_num, filename = match.groups()
                    else:  # file:line or file line X
                        filename, line_num = match.groups()
                    
                    file_ref = self._create_file_reference(
                        filename, query, confidence=0.9, line_number=int(line_num)
                    )
                    if file_ref:
                        file_references.append(file_ref)
        
        # Check direct file patterns
        for pattern in direct_patterns + path_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                filename = match.group(1)
                file_ref = self._create_file_reference(
                    filename, query, confidence=0.8, context=match.group(0)
                )
                if file_ref:
                    file_references.append(file_ref)
        
        # Check common patterns
        for pattern in common_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                pattern_text = match.group(1)
                # Try to resolve common patterns to actual files
                resolved_files = self._resolve_common_patterns(pattern_text)
                for filename in resolved_files:
                    file_ref = self._create_file_reference(
                        filename, query, confidence=0.7, context=pattern_text
                    )
                    if file_ref:
                        file_references.append(file_ref)
        
        # Remove duplicates and sort by confidence
        unique_refs = {}
        for ref in file_references:
            key = ref.filename.lower()
            if key not in unique_refs or ref.confidence > unique_refs[key].confidence:
                unique_refs[key] = ref
        
        file_references = list(unique_refs.values())
        file_references.sort(key=lambda x: x.confidence, reverse=True)
        
        # Determine query type
        query_type = "file_analysis" if file_references else "general"
        if file_references:
            query_type = "file_analysis"
        elif any(word in query_lower for word in ["how", "what", "explain", "analyze"]):
            query_type = "explanation"
        elif any(word in query_lower for word in ["fix", "bug", "error", "issue"]):
            query_type = "debugging"
        elif any(word in query_lower for word in ["add", "create", "implement", "write"]):
            query_type = "generation"
        
        return QueryAnalysis(
            original_query=query,
            file_references=file_references,
            modified_query=query,
            has_file_references=len(file_references) > 0,
            query_type=query_type
        )
    
    def _create_file_reference(self, filename: str, query: str, confidence: float, 
                             context: str = "", line_number: Optional[int] = None) -> Optional[FileReference]:
        """Create a file reference if the file exists."""
        # Try exact filename match first
        if filename in self.file_cache:
            return FileReference(
                filename=filename,
                full_path=self.file_cache[filename],
                confidence=confidence,
                context=context,
                line_number=line_number
            )
        
        # Try case-insensitive match
        filename_lower = filename.lower()
        for cached_filename, full_path in self.file_cache.items():
            if cached_filename.lower() == filename_lower:
                return FileReference(
                    filename=cached_filename,
                    full_path=full_path,
                    confidence=confidence * 0.9,  # Slightly lower confidence for case mismatch
                    context=context,
                    line_number=line_number
                )
        
        # Try partial match (filename contains the pattern)
        for cached_filename, full_path in self.file_cache.items():
            if filename_lower in cached_filename.lower() or cached_filename.lower() in filename_lower:
                return FileReference(
                    filename=cached_filename,
                    full_path=full_path,
                    confidence=confidence * 0.7,  # Lower confidence for partial match
                    context=context,
                    line_number=line_number
                )
        
        return None
    
    def _resolve_common_patterns(self, pattern_text: str) -> List[str]:
        """Resolve common file patterns to actual filenames."""
        resolved = []
        pattern_lower = pattern_text.lower()
        
        # Map common patterns to likely filenames
        pattern_mappings = {
            'deploy': ['deploy.rb', 'deploy.sh', 'deploy.yml', 'deploy.yaml', 'deploy.js', 'deploy.py'],
            'config': ['config.yml', 'config.yaml', 'config.json', 'config.py', 'config.js', 'config.rb'],
            'package.json': ['package.json'],
            'dockerfile': ['Dockerfile', 'dockerfile', 'Dockerfile.dev'],
            'makefile': ['Makefile', 'makefile', 'GNUmakefile'],
            'gemfile': ['Gemfile', 'Gemfile.lock'],
            'requirements': ['requirements.txt', 'requirements-dev.txt', 'requirements-prod.txt'],
            'cargo': ['Cargo.toml', 'Cargo.lock'],
            'go.mod': ['go.mod', 'go.sum'],
        }
        
        for pattern, files in pattern_mappings.items():
            if pattern in pattern_lower:
                for filename in files:
                    if filename in self.file_cache:
                        resolved.append(filename)
        
        return resolved
    
    def get_file_content(self, file_reference: FileReference) -> str:
        """Get the content of a referenced file."""
        if not file_reference.full_path or not os.path.exists(file_reference.full_path):
            return ""
        
        try:
            with open(file_reference.full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # If line number is specified, extract context around that line
            if file_reference.line_number:
                lines = content.split('\n')
                line_idx = file_reference.line_number - 1
                if 0 <= line_idx < len(lines):
                    # Get context around the line (5 lines before and after)
                    start = max(0, line_idx - 5)
                    end = min(len(lines), line_idx + 6)
                    context_lines = lines[start:end]
                    return '\n'.join(context_lines)
            
            return content
        except Exception as e:
            console.print(f"[red]Error reading file {file_reference.full_path}: {e}[/]")
            return ""
