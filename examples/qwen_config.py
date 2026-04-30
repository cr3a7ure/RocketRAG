#!/usr/bin/env python3
"""
Qwen Embedding Configuration Example

This example demonstrates:
- Using Qwen text-embedding-v4 via DashScope API for 1024-dim embeddings
- Semantic chunking for better context preservation
- Question answering with streaming responses

Model: text-embedding-v4 (1024 dimensions)
- High-quality embeddings from Alibaba's Qwen foundation model
- 1024-dimensional output
- Requires DASHSCOPE_API_KEY environment variable

Note: Get your API key at https://dashscope.console.aliyun.com/
"""

import os

from rich.console import Console
from rich.panel import Panel

from rocketrag import RocketRAG
from rocketrag.vectors import QwenEmbeddingVectorizer
from rocketrag.chonk import ChonkieChunker
from rocketrag.loaders import KreuzbergLoader
from rocketrag.llm import LLamaLLM

console = Console()

data_dir = "pdf"
db_path = "qwen_example.db"
collection_name = "qwen_demo"

if not os.environ.get("DASHSCOPE_API_KEY"):
    console.print(
        "[yellow]Warning: DASHSCOPE_API_KEY not set. Qwen vectorizer will fail.[/yellow]"
    )

vectorizer = QwenEmbeddingVectorizer(
    model_name="text-embedding-v4",
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
)

chunker = ChonkieChunker(
    method="semantic",
    embedding_model="minishlab/potion-multilingual-128M",
    chunk_size=512,
    threshold=0.3
)

loader = KreuzbergLoader()

llm = LLamaLLM(
    repo_id="unsloth/gemma-3n-E2B-it-GGUF",
    filename="*Q8_0.gguf"
)


rag = RocketRAG(
    data_dir=data_dir,
    db_path=db_path,
    collection_name=collection_name,
    vectorizer=vectorizer,
    chunker=chunker,
    loader=loader,
    llm=llm,
)

rag.prepare(recreate=True)

questions = [
    "What is the main topic of the documents?",
    "Can you summarize the key findings?",
    "What are the most important points mentioned?",
]


for i, question in enumerate(questions, 1):
    console.print(f"\n[dim]Question {i}: {question}[/dim]")
    answer, sources = rag.ask(question)

    console.print(
        Panel(answer, title="[bold green]Answer[/bold green]", border_style="green")
    )

    if sources:
        console.print("\n[bold]Sources:[/bold]")
        for j, source in enumerate(sources[:3], 1):
            console.print(f"  {j}. {source.filename} (score: {source.score:.3f})")