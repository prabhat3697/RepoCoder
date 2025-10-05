#!/usr/bin/env python3
"""
Pydantic models for RepoCoder API requests and responses.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class IndexRequest(BaseModel):
    folder: Optional[str] = None


class QueryRequest(BaseModel):
    prompt: str
    top_k: int = 12
    max_new_tokens: int = 200  # Reduced for small models
    temperature: float = 0.2


class QueryResponse(BaseModel):
    model: str
    took_ms: int
    retrieved: int
    result: Dict[str, Any]


class ApplyRequest(BaseModel):
    diff: str
