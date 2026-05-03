import os
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
import json
import warnings


# Lazy imports - only import heavy dependencies when needed
def _lazy_imports():
    """Import heavy dependencies only when actually needed."""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    # Set PyTorch environment variable
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    # Suppress pkg_resources deprecation warnings from milvus-lite
    warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")

    # Set environment variables to suppress gRPC warnings
    os.environ["GRPC_VERBOSITY"] = "ERROR"
    os.environ["GRPC_TRACE"] = ""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task_id = progress.add_task("Loading dependencies...", total=None)
        
        progress.update(task_id, description="Loading vector processing...")
        from .vectors import init_vectorizer
        
        progress.update(task_id, description="Loading database components...")
        from .db import MilvusLiteDB
        
        progress.update(task_id, description="Loading chunking components...")
        from .chonk import init_chonker
        
        progress.update(task_id, description="Loading language models...")
        from .llm import LLamaLLM
        
        progress.update(task_id, description="Loading document loaders...")
        from .loaders import init_loader
        
        progress.update(task_id, description="Loading visualization components...")
        from .visualization import VectorVisualizer
        
        progress.update(task_id, description="Loading display utilities...")
        from .display_utils import display_streaming_answer
        
        progress.update(task_id, description="Loading RAG framework...")
        from .rocketrag import RocketRAG
        
        progress.update(task_id, description="Dependencies loaded ✓")

    return {
        "init_vectorizer": init_vectorizer,
        "MilvusLiteDB": MilvusLiteDB,
        "init_chonker": init_chonker,
        "LLamaLLM": LLamaLLM,
        "init_loader": init_loader,
        "VectorVisualizer": VectorVisualizer,
        "display_streaming_answer": display_streaming_answer,
        "RocketRAG": RocketRAG,
    }


app = typer.Typer()


@app.command()
def prepare(
    data_dir: list[str] = typer.Argument(
        ..., help="Directory(s) containing documents to process"
    ),
    chonker: str = typer.Option(
        "chonkie", help="Chunking strategy to use (e.g., 'chonkie')"
    ),
    chonker_args: str = typer.Option(
        '{"method": "recursive", "chunk_size": 500}',
        help="JSON string with chunker configuration arguments",
    ),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration arguments",
    ),
    loader: str = typer.Option(
        "kreuzberg", help="Document loader to use (e.g., 'kreuzberg')"
    ),
    loader_args: str = typer.Option(
        "{}", help="JSON string with loader configuration arguments"
    ),
    max_workers: int = typer.Option(
        4, help="Number of parallel workers for file extraction"
    ),
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option(
        "rag", help="Name of the collection in the database"
    ),
    recreate: bool = typer.Option(False, help="Recreate the collection if it exists"),
    dry_run: bool = typer.Option(False, help="Check files without inserting to database"),
    incremental: bool = typer.Option(False, help="Only index files that have changed"),
):
    """Prepare the RAG system by processing documents and creating embeddings."""
    imports = _lazy_imports()

    print(Panel("[bold blue]Preparing RAG system...[/bold blue]"))

    chonker_args_dict = json.loads(chonker_args)
    vectorizer_args_dict = json.loads(vectorizer_args)
    loader_args_dict = json.loads(loader_args)

    vectorizer = imports["init_vectorizer"](
        "sentence_transformers", **vectorizer_args_dict
    )
    chunker = imports["init_chonker"](chonker, **chonker_args_dict)
    loader = imports["init_loader"](loader, max_workers=max_workers, **loader_args_dict)

    for directory in data_dir:
        if not os.path.isdir(directory):
            console = Console()
            console.print(
                Panel(
                    f"Directory not found: {directory}",
                    title="Error",
                    border_style="red",
                )
            )
            continue

        print(f"\n[bold cyan]Processing directory: {directory}[/bold cyan]")
        rag = imports["RocketRAG"](
            directory,
            db_path,
            collection_name,
            vectorizer,
            chunker,
            loader,
        )
        if dry_run:
            docs = rag.prepare(recreate, dry_run=True)
            if docs:
                print(f"[bold green]Dry-run: Would process {len(docs)} file(s)[/bold green]")
                for doc in docs:
                    print(f"  - {doc.filename} ({len(doc.chunks)} chunks)")
            continue
        rag.prepare(recreate, incremental=incremental)


@app.command()
def llm(
    question: str = typer.Argument(..., help="Question to ask the LLM directly"),
    repo_id: str = typer.Option(
        "unsloth/gemma-3n-E2B-it-GGUF",
        help="Hugging Face repository ID for the LLM model",
    ),
    filename: str = typer.Option(
        "*Q8_0.gguf", help="Model filename pattern to load from the repository"
    ),
):
    """Query the LLM directly"""
    imports = _lazy_imports()
    llm = imports["LLamaLLM"](repo_id, filename)
    stream = llm.stream([{"role": "user", "content": question}])
    imports["display_streaming_answer"](question, stream)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask the RAG system"),
    repo_id: str = typer.Option(
        "unsloth/gemma-3n-E2B-it-GGUF",
        help="Hugging Face repository ID for the LLM model",
    ),
    filename: str = typer.Option(
        "*Q8_0.gguf", help="Model filename pattern to load from the repository"
    ),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration arguments",
    ),
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: list[str] = typer.Option(
        None, help="Collection name(s) to search (can specify multiple)"
    ),
    all_collections: bool = typer.Option(
        False, "--all", help="Search all collections"
    ),
):
    collections = None
    if all_collections:
        collections = ["__all__"]
    elif collection_name:
        collections = collection_name

    imports = _lazy_imports()

    vectorizer_config = json.loads(vectorizer_args)
    vectorizer = imports["init_vectorizer"](
        "sentence_transformers", **vectorizer_config
    )

    llm = imports["LLamaLLM"](**{"repo_id": repo_id, "filename": filename})

    rag = imports["RocketRAG"](
        db_path=db_path,
        collection_name="rag",
        vectorizer=vectorizer,
        llm=llm,
    )
    stream, sources = rag.stream_ask(question, collection_names=collections)
    imports["display_streaming_answer"](question, stream, sources)


@app.command()
def server(
    repo_id: str = typer.Option(
        "unsloth/gemma-3n-E2B-it-GGUF",
        help="Hugging Face repository ID for the LLM model",
    ),
    filename: str = typer.Option(
        "*Q8_0.gguf", help="Model filename pattern to load from the repository"
    ),
    port: int = typer.Option(8000, help="Port number to run the server on"),
    host: str = typer.Option("127.0.0.1", help="Host address to bind the server to"),
    chonker: str = typer.Option(
        "chonkie", help="Chunking strategy to use (e.g., 'chonkie')"
    ),
    chonker_args: str = typer.Option(
        '{"method": "recursive", "chunk_size": 500}',
        help="JSON string with chunker configuration arguments",
    ),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration arguments",
    ),
    loader: str = typer.Option(
        "kreuzberg", help="Document loader to use (e.g., 'kreuzberg')"
    ),
    loader_args: str = typer.Option(
        "{}", help="JSON string with loader configuration arguments"
    ),
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option(
        "rag", help="Name of the collection in the database"
    ),
):
    """Start the RAG web server"""
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    from .webserver import start_server

    print(f"Starting rocketrag server on {host}:{port}")

    imports = _lazy_imports()

    # Parse JSON arguments for server configuration
    chonker_config = json.loads(chonker_args)
    vectorizer_config = json.loads(vectorizer_args)
    loader_config = json.loads(loader_args)
    vectorizer = imports["init_vectorizer"](
        "sentence_transformers", **vectorizer_config
    )
    chunker = imports["init_chonker"](chonker, **chonker_config)
    loader = imports["init_loader"](loader, **loader_config)
    rag = imports["RocketRAG"](
        db_path=db_path,
        collection_name=collection_name,
        vectorizer=vectorizer,
        chunker=chunker,
        loader=loader,
    )
    start_server(rag, port=port, host=host)


@app.command()
def visualize(
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option(
        "rag", help="Name of the collection in the database"
    ),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration arguments",
    ),
    limit: int = typer.Option(
        500, help="Maximum number of vectors to visualize (for performance)"
    ),
    filename_filter: str = typer.Option(
        None, help="Filter vectors by specific filename"
    ),
    question: str = typer.Option(
        None, help="Question to encode and visualize on the map with similar chunks"
    ),
):
    """Visualize the vector space in the database"""
    console = Console()

    imports = _lazy_imports()

    try:
        vectorizer_config = json.loads(vectorizer_args)
        vectorizer = imports["init_vectorizer"](
            "sentence_transformers", **vectorizer_config
        )

        db = imports["MilvusLiteDB"](
            db_path=db_path, collection_name=collection_name, vectorizer=vectorizer
        )

        if collection_name not in db.client.list_collections():
            console.print(
                Panel(
                    f"Collection '{collection_name}' not found. Run 'prepare' command first.",
                    title="Error",
                    border_style="red",
                )
            )
            return

        if filename_filter:
            records = db.get_vectors_by_filename(filename_filter)
            title_suffix = f" - {filename_filter}"
        else:
            records = db.get_vectors_with_metadata(limit=limit)
            title_suffix = (
                f" (showing {min(limit, len(records))} vectors)"
                if len(records) == limit
                else ""
            )

        if not records:
            console.print(
                Panel(
                    "No vectors found in the database.",
                    title="No Data",
                    border_style="yellow",
                )
            )
            return

        vectors = [record["vector"] for record in records]
        metadata = [
            {"id": record["id"], "text": record["text"], "filename": record["filename"]}
            for record in records
        ]

        visualizer = imports["VectorVisualizer"](console=console)

        with console.status("[bold green]Analyzing vectors..."):
            analysis_result = visualizer.analyze_vectors(vectors, metadata)

        if "error" in analysis_result:
            console.print(
                Panel(
                    f"Analysis error: {analysis_result['error']}",
                    title="Error",
                    border_style="red",
                )
            )
            return

        question_point = None
        similar_chunks = None

        if question:
            with console.status("[bold green]Processing question..."):
                question_result = visualizer.process_question(
                    question, vectors, metadata, analysis_result, vectorizer
                )
                if "error" not in question_result:
                    question_point = question_result.get("question_point")
                    similar_chunks = question_result.get("similar_chunks")

        console.print("\n")
        console.print(
            visualizer.create_visualization_panel(
                analysis_result,
                title=f"Vector Space Visualization{title_suffix}",
                color_by="filename",
                question_point=question_point,
                question_text=question,
            )
        )

        if similar_chunks:
            console.print("\n")
            console.print(
                visualizer.create_similar_chunks_panel(similar_chunks, question)
            )

        console.print("\n[dim]Visualization complete![/dim]")

    except json.JSONDecodeError as e:
        console.print(
            Panel(
                f"Invalid JSON in arguments: {e}",
                title="Configuration Error",
                border_style="red",
            )
        )
    except Exception as e:
        console.print(
            Panel(f"Visualization error: {e}", title="Error", border_style="red")
        )


@app.command()
def mcp_server(
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option("rag", help="Name of the collection"),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration",
    ),
    transport: str = typer.Option("stdio", help="Transport type (stdio or http)"),
    host: str = typer.Option("127.0.0.1", help="Host for HTTP transport"),
    port: int = typer.Option(8000, help="Port for HTTP transport"),
):
    """Start the RocketRAG MCP server for database querying."""
    from .mcp_server import run_stdio, run_http

    vectorizer_args_dict = json.loads(vectorizer_args)

    if transport == "http":
        run_http(db_path, collection_name, vectorizer_args_dict, host, port)
    else:
        run_stdio(db_path, collection_name, vectorizer_args_dict)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option("rag", help="Collection to search"),
    top_k: int = typer.Option(5, help="Number of results to return"),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration",
    ),
):
    """Search the vector database for relevant chunks."""
    imports = _lazy_imports()

    vectorizer_config = json.loads(vectorizer_args)
    vectorizer = imports["init_vectorizer"](
        "sentence_transformers", **vectorizer_config
    )

    db = imports["MilvusLiteDB"](
        db_path=db_path,
        collection_name=collection_name,
        vectorizer=vectorizer,
    )

    results = db.search(query, top_k=top_k)
    console = Console()

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    from rich.table import Table
    table = Table(title=f"Search results for: {query}")
    table.add_column("Score", style="green", width=10)
    table.add_column("File", style="cyan")
    table.add_column("Chunk", style="white")

    for r in results:
        chunk_preview = r.chunk[:100] + "..." if len(r.chunk) > 100 else r.chunk
        table.add_row(f"{r.score:.4f}", r.filename, chunk_preview)

    console.print(table)


@app.command()
def list_files(
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option("rag", help="Collection to query"),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration",
    ),
):
    """List all files indexed in the database."""
    imports = _lazy_imports()

    vectorizer_config = json.loads(vectorizer_args)
    vectorizer = imports["init_vectorizer"](
        "sentence_transformers", **vectorizer_config
    )

    db = imports["MilvusLiteDB"](
        db_path=db_path,
        collection_name=collection_name,
        vectorizer=vectorizer,
    )

    files = db.get_unique_filenames()
    console = Console()

    console.print(f"[bold]Total files: {len(files)}[/bold]")
    for f in sorted(files):
        console.print(f"  • {f}")


@app.command()
def stats(
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option("rag", help="Collection to query"),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration",
    ),
):
    """Show database statistics."""
    imports = _lazy_imports()

    vectorizer_config = json.loads(vectorizer_args)
    vectorizer = imports["init_vectorizer"](
        "sentence_transformers", **vectorizer_config
    )

    db = imports["MilvusLiteDB"](
        db_path=db_path,
        collection_name=collection_name,
        vectorizer=vectorizer,
    )

    total = db.get_total_count()
    files = db.get_unique_filenames()
    metadata = db.get_collection_metadata()

    console = Console()
    console.print(Panel(
        f"[bold]Total chunks:[/bold] {total}\n"
        f"[bold]Unique files:[/bold] {len(files)}\n"
        f"[bold]Dimension:[/bold] {db.dimension}\n"
        f"[bold]Vectorizer:[/bold] {metadata.get('vectorizer', 'unknown')}\n"
        f"[bold]Loader:[/bold] {metadata.get('loader', 'unknown')}\n"
        f"[bold]Chunker:[/bold] {metadata.get('chonker', 'unknown')}",
        title="Database Statistics",
        border_style="cyan"
    ))


@app.command()
def ingest(
    directory: str = typer.Argument(..., help="Directory to ingest"),
    db_path: str = typer.Option("rag.db", help="Path to the database file"),
    collection_name: str = typer.Option("localdev", help="Collection name"),
    max_workers: int = typer.Option(4, help="Parallel workers for extraction"),
    incremental: bool = typer.Option(True, help="Only index changed files"),
    recreate: bool = typer.Option(False, help="Recreate collection before ingesting"),
    chonker_args: str = typer.Option(
        '{"method": "recursive", "chunk_size": 500}',
        help="JSON string with chunker configuration",
    ),
    vectorizer_args: str = typer.Option(
        '{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration",
    ),
):
    """Ingest a directory into the vector database."""
    imports = _lazy_imports()

    if not os.path.isdir(directory):
        console = Console()
        console.print(Panel(f"Directory not found: {directory}", title="Error", border_style="red"))
        return

    chonker_config = json.loads(chonker_args)
    vectorizer_config = json.loads(vectorizer_args)

    vectorizer = imports["init_vectorizer"](
        "sentence_transformers", **vectorizer_config
    )
    chunker = imports["init_chonker"]("chonkie", **chonker_config)
    loader = imports["init_loader"]("kreuzberg", max_workers=max_workers)

    from .utils import construct_metadata_dict, get_git_repo_info

    git_repo_info = get_git_repo_info(directory)
    metadata = construct_metadata_dict(
        directory, chunker, chunker.config, vectorizer, vectorizer.config,
        loader, loader.config, db_path, collection_name, git_repo_info=git_repo_info
    )

    db = imports["MilvusLiteDB"](
        db_path=db_path,
        collection_name=collection_name,
        vectorizer=vectorizer,
        chunker=chunker,
        metadata=metadata,
    )

    documents = loader.load_files_from_dir(directory)
    files_processed = len(documents)

    if incremental:
        stale = db.get_stale_filenames(documents)
        if stale:
            console = Console()
            console.print(f"Incremental: {len(stale)} file(s) changed, re-indexing...")
            documents = [d for d in documents if (d.filepath or d.filename) in stale]
        else:
            console = Console()
            console.print("Incremental: No files changed, skipping ingestion.")
            return

    if not documents:
        return

    if recreate:
        db.client.drop_collection(collection_name)

    db.create_collection_if_not_exists(recreate=False)
    db.add_documents(documents)

    if incremental:
        db.update_file_index(documents)

    total_chunks = sum(len(doc.chunks) for doc in documents)
    console = Console()
    console.print(Panel(
        f"[bold]Files processed:[/bold] {files_processed}\n"
        f"[bold]Chunks added:[/bold] {total_chunks}\n"
        f"[bold]Collection:[/bold] {collection_name}",
        title="Ingest Complete",
        border_style="green"
    ))


@app.command()
def check(
    data_dir: str = typer.Argument(".", help="Directory to scan"),
    disable_ocr: bool = typer.Option(False, help="Disable OCR when scanning"),
):
    """Diagnose and find problematic files in a directory."""
    from pathlib import Path
    from kreuzberg import extract_file_sync, ExtractionConfig
    from rich.console import Console
    from rich.table import Table

    console = Console()
    config = ExtractionConfig(disable_ocr=disable_ocr)

    results = {"pdf": [], "images": [], "other": [], "errors": []}
    image_exts = {"jpg", "jpeg", "png", "tiff", "bmp", "gif", "webp"}

    console.print(f"[cyan]Scanning: {data_dir}[/cyan]")
    console.print()

    for root, dirs, files in os.walk(data_dir):
        dirs[:] = [d for d in dirs if d != ".git"]

        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            ext = Path(filename).suffix.lower().lstrip(".")

            if ext == "pdf":
                try:
                    extract_file_sync(filepath, config=config)
                    results["pdf"].append((filename, filepath, "OK"))
                except Exception as e:
                    results["pdf"].append((filename, filepath, f"FAIL: {type(e).__name__}"))
                    results["errors"].append(filepath)
            elif ext in image_exts:
                try:
                    extract_file_sync(filepath, config=config)
                    results["images"].append((filename, filepath, "OK"))
                except Exception as e:
                    results["images"].append((filename, filepath, f"FAIL: {type(e).__name__}"))
                    results["errors"].append(filepath)

    if results["pdf"]:
        table = Table(title="PDF Files")
        table.add_column("Status", style="green", width=8)
        table.add_column("File", style="cyan")
        for filename, filepath, status in results["pdf"]:
            style = "green" if status == "OK" else "red"
            table.add_row(status, filepath)

        console.print(table)

    if results["images"]:
        table = Table(title="Image Files")
        table.add_column("Status", style="green", width=8)
        table.add_column("File", style="cyan")
        for filename, filepath, status in results["images"]:
            style = "green" if status == "OK" else "red"
            table.add_row(status, filepath)

        console.print(table)

    if results["errors"]:
        console.print()
        console.print(f"[bold red]Found {len(results['errors'])} problematic files:[/bold red]")
        for filepath in results["errors"]:
            console.print(f"  [red]•[/red] {filepath}")
    else:
        console.print()
        console.print("[bold green]No problems found![/bold green]")

    return len(results["errors"]) > 0


def main():
    app()


if __name__ == "__main__":
    app()
