from pathlib import Path
from mcp.server.fastmcp import FastMCP
from .db import MilvusLiteDB
from .vectors import init_vectorizer


def create_mcp_server(
    db_path: str,
    collection_name: str,
    vectorizer_args: dict,
    host: str = "127.0.0.1",
    port: int = 8000,
    library_db_path: str = None,
):
    """Create an MCP server for querying the RocketRAG database.

    Supports dynamic local DB loading based on project path:
    - Local DB: Auto-discovered from project root (project_path/rag.db)
    - Library DB (library_db_path): Pre-ingested company/library documentation

    All search tools query both databases (when available) and return merged results with
    an 'origin' field indicating 'local' or 'library'.

    Args:
        db_path: Default path for local database (used if no project_path specified)
        collection_name: Collection name for databases
        vectorizer_args: Vectorizer configuration
        host: HTTP host for server
        port: HTTP port for server
        library_db_path: Optional path to library/company documentation database
    """
    vectorizer = init_vectorizer("sentence_transformers", **vectorizer_args)

    _default_local_db_path = db_path
    _default_collection_name = collection_name
    _library_db = None

    if library_db_path:
        _library_db = MilvusLiteDB(
            db_path=library_db_path,
            collection_name=collection_name,
            vectorizer=vectorizer,
        )

    def _get_local_db(project_path: str = None):
        """Get or create local DB for project_path.

        Auto-discovers rag.db in project root. Caches DB instance for reuse.
        If project_path is None, uses current working directory.

        Args:
            project_path: Path to project root (auto-discovers project_path/rag.db)

        Returns:
            MilvusLiteDB instance or None if no database found
        """
        # Use cwd if no project_path provided
        target_path = Path(project_path) if project_path else Path.cwd()
        db_file = target_path / "rag.db"

        # Return None if no database file exists
        if not db_file.exists():
            return None

        # Create cache key based on resolved path
        cache_key = str(target_path.resolve())

        # Check if we already have this DB loaded
        if hasattr(_get_local_db, '_cache') and cache_key in _get_local_db._cache:
            return _get_local_db._cache[cache_key]

        # Initialize cache if needed
        if not hasattr(_get_local_db, '_cache'):
            _get_local_db._cache = {}

        # Load and cache the database
        local_db = MilvusLiteDB(
            db_path=str(db_file),
            collection_name=collection_name,
            vectorizer=vectorizer,
        )
        _get_local_db._cache[cache_key] = local_db
        return local_db

    def _get_all_databases(project_path: str = None):
        """Get all available databases for querying.

        Args:
            project_path: Optional project path for local DB discovery

        Returns:
            Dict of {label: db_instance} with 'local' and optionally 'library'
        """
        result = {}
        local_db = _get_local_db(project_path)
        if local_db:
            result["local"] = local_db
        if _library_db:
            result["library"] = _library_db
        return result

    mcp = FastMCP(
        "RocketRAG Query Server",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )

    def _search_db(db_instance, query, top_k, filter_expr):
        """Helper to search a single database and tag results."""
        results = db_instance.search(query, top_k=top_k, filter=filter_expr)
        return [
            {
                "chunk": r.chunk,
                "filename": r.filename,
                "score": r.score,
                "source": r.source or "",
                "language": r.language or "",
                "project_name": r.project_name or "",
            }
            for r in results
        ]

    @mcp.tool()
    def quick_search(project_path: str, query: str, top_k: int = 5) -> list[dict]:
        """Search with project context - auto-resolves dependencies from both local and library databases.

        Reads package.json, pyproject.toml from project_path to discover the project
        and its dependencies, then searches BOTH your local database AND the library
        database, filtering to matching projects.

        Results are merged and sorted by score, with an 'origin' field showing
        'local' (your codebase) or 'library' (company docs).

        Args:
            project_path: Path to your local project (reads package.json, pyproject.toml)
            query: The search query text
            top_k: Number of results to return (default: 5)

        Returns:
            List of search results from project and its dependencies in both databases.
            Each result includes an 'origin' field: 'local' or 'library'.
        """
        try:
            from .utils import get_project_name
            import json

            path = Path(project_path)
            project_names = []

            pkg_json = path / "package.json"
            if pkg_json.exists():
                try:
                    with open(pkg_json) as f:
                        data = json.load(f)
                        if data.get("name"):
                            project_names.append(data["name"])
                        deps = data.get("dependencies", {})
                        project_names.extend(deps.keys())
                        dev_deps = data.get("devDependencies", {})
                        project_names.extend(dev_deps.keys())
                except (json.JSONDecodeError, OSError):
                    pass

            pyproject = path / "pyproject.toml"
            if pyproject.exists():
                try:
                    import tomllib
                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)
                        if "project" in data and data["project"].get("name"):
                            project_names.append(data["project"]["name"])
                        if "project" in data and data["project"].get("dependencies"):
                            project_names.extend(data["project"]["dependencies"])
                except (json.JSONDecodeError, OSError):
                    pass

            if not project_names:
                project_names.append(get_project_name(str(path)) or path.name)

            filter_expr = f'project_name in {project_names}'

            all_results = []
            for label, db_instance in _get_all_databases(project_path).items():
                try:
                    results = _search_db(db_instance, query, top_k, filter_expr)
                    for r in results:
                        r["origin"] = label
                    all_results.extend(results)
                except Exception:
                    continue

            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:top_k]
        except Exception as e:
            return [{"error": str(e), "results": []}]

    @mcp.tool()
    def deep_search(query: str, top_k: int = 5, collection_name: str = None, filter: str = None) -> list[dict]:
        """Full-depth search across both local and library databases - no project filtering.

        Use this for exploratory search when you want results from ALL indexed content
        in both your local database and the library database.

        Results are merged and sorted by score, with an 'origin' field showing
        'local' or 'library'.

        Args:
            query: The search query text
            top_k: Number of results to return (default: 5)
            collection_name: Specific collection to search (default: searches all)
            filter: Optional Milvus filter expression for additional filtering

        Returns:
            List of all search results from both databases.
            Each result includes an 'origin' field: 'local' or 'library'.
        """
        try:
            all_results = []
            for label, db_instance in _get_all_databases().items():
                try:
                    results = _search_db(db_instance, query, top_k, filter)
                    for r in results:
                        r["origin"] = label
                    all_results.extend(results)
                except Exception:
                    continue

            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:top_k]
        except Exception as e:
            return [{"error": str(e), "results": []}]

    @mcp.tool()
    def search_all(query: str, top_k: int = 5, filter: str = None) -> list[dict]:
        """Search ALL collections in all databases for relevant chunks.

        Searches both local and library databases, merging results and sorting by score.
        Each result includes an 'origin' field showing 'local' or 'library'.

        Args:
            query: The search query text
            top_k: Number of results to return (default: 5)
            filter: Milvus filter expression (e.g., 'source like "%auth%"')

        Returns:
            List of search results with chunk text, filename, score, source, and origin.
            Each result includes an 'origin' field: 'local' or 'library'.
        """
        try:
            all_results = []
            for label, db_instance in _get_all_databases().items():
                try:
                    results = _search_db(db_instance, query, top_k, filter)
                    for r in results:
                        r["origin"] = label
                    all_results.extend(results)
                except Exception:
                    continue

            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:top_k]
        except Exception as e:
            return [{"error": str(e), "results": []}]

    @mcp.tool()
    def list_files() -> list[str]:
        """List all unique filenames indexed in all databases.

        Returns:
            List of unique filenames from all databases
        """
        try:
            all_files = set()
            for label, db_instance in _get_all_databases().items():
                try:
                    files = db_instance.get_unique_filenames()
                    all_files.update(files)
                except Exception:
                    continue
            return sorted(list(all_files))
        except Exception as e:
            return [f"error: {str(e)}"]

    @mcp.tool()
    def get_file_chunks(filename: str) -> list[dict]:
        """Get all chunks from a specific file across all databases.

        Args:
            filename: The filename to retrieve chunks for

        Returns:
            List of chunks with text and id from all databases
        """
        try:
            all_chunks = []
            for label, db_instance in _get_all_databases().items():
                try:
                    results = db_instance.get_vectors_by_filename(filename)
                    for r in results:
                        r["origin"] = label
                        all_chunks.append(r)
                except Exception:
                    continue
            return [
                {
                    "id": r["id"],
                    "text": r["text"],
                    "origin": r.get("origin", "unknown"),
                }
                for r in all_chunks
            ]
        except Exception as e:
            return [{"error": str(e)}]

    @mcp.tool()
    def get_stats() -> dict:
        """Get aggregated database statistics from all databases.

        Returns:
            Dictionary with total_chunks, unique_files, databases, and per-database stats
        """
        try:
            total = 0
            all_files = set()
            dimensions = set()
            models = set()
            db_stats = []

            for label, db_instance in _get_all_databases().items():
                try:
                    db_total = db_instance.get_total_count()
                    db_files = db_instance.get_unique_filenames()
                    db_meta = db_instance.get_collection_metadata()
                    db_dim = db_instance.dimension

                    total += db_total
                    all_files.update(db_files)
                    dimensions.add(db_dim)
                    models.add(db_meta.get("vectorizer_args", {}).get("model_name", "unknown"))

                    db_stats.append({
                        "name": label,
                        "chunks": db_total,
                        "files": len(db_files),
                        "dimension": db_dim,
                        "model": db_meta.get("vectorizer_args", {}).get("model_name", "unknown"),
                    })
                except Exception:
                    continue

            return {
                "total_chunks": total,
                "unique_files": len(all_files),
                "databases": db_stats,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_all_chunks(limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all chunks with pagination from all databases.

        Args:
            limit: Maximum number of chunks to return (default: 100)
            offset: Number of chunks to skip (default: 0)

        Returns:
            List of chunks with text and filename from all databases
        """
        try:
            all_chunks = []
            for label, db_instance in _get_all_databases().items():
                try:
                    results = db_instance.get_all_records(limit=limit, offset=offset)
                    for r in results:
                        r["origin"] = label
                        all_chunks.append(r)
                except Exception:
                    continue
            return [
                {
                    "id": r["id"],
                    "text": r["text"],
                    "filename": r["filename"],
                    "origin": r.get("origin", "unknown"),
                }
                for r in all_chunks
            ]
        except Exception as e:
            return [{"error": str(e)}]

    @mcp.tool()
    def ingest_directory(
        directory: str,
        collection_name: str = "localdev",
        max_workers: int = 4,
        incremental: bool = True,
        recreate: bool = False,
        db_path: str = None,
    ) -> dict:
        """Ingest a directory of documents into the vector database.

        Args:
            directory: Path to the directory to ingest
            collection_name: Name of the collection (default: localdev)
            max_workers: Number of parallel workers for extraction (default: 4)
            incremental: Only index changed files (default: True)
            recreate: Recreate collection before ingesting (default: False)
            db_path: Optional path to a separate database file for project-local storage.
                    If not provided, uses the server's default database.

        Returns:
            Dictionary with status, files_processed, and chunks_added
        """
        try:
            from .loaders import init_loader
            from .chonk import init_chonker
            from .vectors import init_vectorizer
            from .utils import construct_metadata_dict, get_git_repo_info, get_project_name

            target_db_path = db_path if db_path else str(Path(directory) / "rag.db")
            target_collection = collection_name or _default_collection_name

            loader = init_loader("kreuzberg", max_workers=max_workers)
            chunker = init_chonker("chonkie", method="semantic", chunk_size=512)
            vectorizer = init_vectorizer(
                "sentence_transformers",
                model_name=vectorizer_args.get("model_name", "minishlab/potion-multilingual-128M"),
            )

            git_repo_info = get_git_repo_info(directory)
            project_name = get_project_name(directory)
            metadata = construct_metadata_dict(
                directory, chunker, chunker.config, vectorizer, vectorizer.config, loader, loader.config, target_db_path, target_collection, git_repo_info=git_repo_info
            )

            from .db import MilvusLiteDB
            target_db = MilvusLiteDB(
                db_path=target_db_path,
                collection_name=target_collection,
                vectorizer=vectorizer,
                chunker=chunker,
                metadata=metadata,
            )

            documents = loader.load_files_from_dir(directory)
            for doc in documents:
                doc.project_name = project_name
            files_processed = len(documents)

            if incremental:
                stale = target_db.get_stale_filenames(documents)
                if stale:
                    documents = [d for d in documents if (d.filepath or d.filename) in stale]
                else:
                    documents = []

            if not documents:
                return {
                    "status": "skipped",
                    "message": "No files changed, skipping ingestion",
                    "files_processed": 0,
                    "chunks_added": 0,
                }

            if recreate:
                target_db.client.drop_collection(target_collection)

            target_db.create_collection_if_not_exists(recreate=False)
            target_db.add_documents(documents)

            if incremental:
                target_db.update_file_index(documents)

            total_chunks = sum(len(doc.chunks) for doc in documents)

            return {
                "status": "success",
                "files_processed": files_processed,
                "chunks_added": total_chunks,
                "collection": target_collection,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return mcp


def run_stdio(db_path: str, collection_name: str, vectorizer_args: dict, library_db_path: str = None):
    """Run MCP server with stdio transport."""
    mcp = create_mcp_server(db_path, collection_name, vectorizer_args, library_db_path=library_db_path)
    mcp.run(transport="stdio")


def run_http(db_path: str, collection_name: str, vectorizer_args: dict, host: str = "127.0.0.1", port: int = 8000, library_db_path: str = None):
    """Run MCP server with HTTP transport via SSE."""
    import uvicorn
    from fastapi import FastAPI

    mcp = create_mcp_server(db_path, collection_name, vectorizer_args, host=host, port=port, library_db_path=library_db_path)
    sse_app = mcp.sse_app()

    app = FastAPI(title="RocketRAG MCP Server")

    @app.get("/")
    async def root():
        return {"service": "RocketRAG MCP Server", "version": "1.0"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    app.mount("/mcp", sse_app)

    uvicorn.run(app, host=host, port=port)


def main():
    """Run the MCP server from command line."""
    import argparse
    import json
    import os

    parser = argparse.ArgumentParser(description="RocketRAG MCP Server")
    parser.add_argument("--db-path", default="rag.db", help="Path to local user's database")
    parser.add_argument("--library-db-path", default=None, help="Path to library/company documentation database")
    parser.add_argument("--collection-name", default="rag", help="Name of the collection")
    parser.add_argument(
        "--vectorizer-args",
        default='{"model_name": "minishlab/potion-multilingual-128M"}',
        help="JSON string with vectorizer configuration",
    )
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"], help="Transport type")
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transport")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transport")

    args = parser.parse_args()

    vectorizer_args = json.loads(args.vectorizer_args)
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    if args.transport == "http":
        run_http(args.db_path, args.collection_name, vectorizer_args, args.host, args.port, args.library_db_path)
    else:
        run_stdio(args.db_path, args.collection_name, vectorizer_args, args.library_db_path)


if __name__ == "__main__":
    main()