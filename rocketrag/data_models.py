from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    content: str
    filename: str
    chunks: list[str] = field(default_factory=list)
    language: Optional[str] = None
    filepath: Optional[str] = None


@dataclass
class SearchResult:
    chunk: str
    filename: str
    score: float
    language: Optional[str] = None
    filepath: Optional[str] = None
