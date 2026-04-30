#!/usr/bin/env python3
"""
E5 Embedding Configuration Example

This example demonstrates:
- Using intfloat/e5-base-v2 for high-quality embeddings
- Semantic chunking for better context preservation
- Code file ingestion with AST-based chunking
- Question answering with streaming responses

Model: intfloat/e5-base-v2 (768 dimensions)
- General-purpose embeddings with strong performance
- Works well on technical/code content
- 768-dimensional output

Note: E5 models expect prompts to be prefixed with "query: " or "passage: "
for retrieval tasks. This is handled automatically in the vectorizer.
"""

from rich.console import Console
from rich.panel import Panel

from rocketrag import RocketRAG
from rocketrag.vectors import SentenceTransformersVectorizer
from rocketrag.chonk import ChonkieChunker
from rocketrag.loaders import KreuzbergLoader
from rocketrag.llm import LLamaLLM

console = Console()

data_dir = "pdf"
db_path = "e5_example.db"
collection_name = "e5_demo"


vectorizer = SentenceTransformersVectorizer(
    model_name="intfloat/e5-base-v2"
)

chunker = ChonkieChunker(
    method="semantic",
    embedding_model="intfloat/e5-base-v2",
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
