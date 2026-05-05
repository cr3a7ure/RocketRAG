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
):
    """Create an MCP server for querying the RocketRAG database."""
    vectorizer = init_vectorizer("sentence_transformers", **vectorizer_args)

    db = MilvusLiteDB(
        db_path=db_path,
        collection_name=collection_name,
        vectorizer=vectorizer,
    )

    mcp = FastMCP(
        "RocketRAG Query Server",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )

    @mcp.tool()
    def quick_search(project_path: str, query: str, top_k: int = 5) -> list[dict]:
        """Search with project context - auto-resolves dependencies and filters.

        Reads package.json, pyproject.toml, etc. from project_path to discover
        the project and its dependencies, then filters search to those packages.

        Args:
            project_path: Path to local project (reads package.json, pyproject.toml, etc.)
            query: The search query text
            top_k: Number of results to return (default: 5)

        Returns:
            List of search results from project and its dependencies
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
            results = db.search(query, top_k=top_k, filter=filter_expr)
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
        except Exception as e:
            return [{"error": str(e), "results": []}]

    @mcp.tool()
    def deep_search(query: str, top_k: int = 5, collection_name: str = None, filter: str = None) -> list[dict]:
        """Full-depth search without project filtering - searches everything.

        Use this for exploratory search or when you want results from all projects.

        Args:
            query: The search query text
            top_k: Number of results to return (default: 5)
            collection_name: Specific collection to search (default: search default)
            filter: Optional Milvus filter expression for additional filtering

        Returns:
            List of search results with chunk, filename, score, source, language, project_name
        """
        try:
            results = db.search(query, top_k=top_k, collection_name=collection_name, filter=filter)
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
        except Exception as e:
            return [{"error": str(e), "results": []}]

    @mcp.tool()
    def search_all(query: str, top_k: int = 5, filter: str = None) -> list[dict]:
        """Search ALL collections in the database for relevant chunks.

        Args:
            query: The search query text
            top_k: Number of results to return (default: 5)
            filter: Milvus filter expression (e.g., 'source like "%auth%"')

        Returns:
            List of search results with chunk text, filename, score, and source
        """
        try:
            results = db.search_all(query, top_k=top_k)
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
        except Exception as e:
            return [{"error": str(e), "results": []}]

    @mcp.tool()
    def list_files() -> list[str]:
        """List all unique filenames indexed in the database.

        Returns:
            List of unique filenames
        """
        try:
            return db.get_unique_filenames()
        except Exception as e:
            return [f"error: {str(e)}"]

    @mcp.tool()
    def get_file_chunks(filename: str) -> list[dict]:
        """Get all chunks from a specific file.

        Args:
            filename: The filename to retrieve chunks for

        Returns:
            List of chunks with text and id
        """
        try:
            results = db.get_vectors_by_filename(filename)
            return [
                {
                    "id": r["id"],
                    "text": r["text"],
                }
                for r in results
            ]
        except Exception as e:
            return [{"error": str(e)}]

    @mcp.tool()
    def get_stats() -> dict:
        """Get database statistics.

        Returns:
            Dictionary with total_chunks, unique_files, dimension, and vectorizer_model
        """
        try:
            total = db.get_total_count()
            files = db.get_unique_filenames()
            metadata = db.get_collection_metadata()

            return {
                "total_chunks": total,
                "unique_files": len(files),
                "dimension": db.dimension,
                "vectorizer_model": metadata.get("vectorizer_args", {}).get("model_name", "unknown"),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_all_chunks(limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all chunks with pagination.

        Args:
            limit: Maximum number of chunks to return (default: 100)
            offset: Number of chunks to skip (default: 0)

        Returns:
            List of chunks with text and filename
        """
        try:
            results = db.get_all_records(limit=limit, offset=offset)
            return [
                {
                    "id": r["id"],
                    "text": r["text"],
                    "filename": r["filename"],
                }
                for r in results
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
    ) -> dict:
        """Ingest a directory of documents into the vector database.

        Args:
            directory: Path to the directory to ingest
            collection_name: Name of the collection (default: server's collection)
            max_workers: Number of parallel workers for extraction (default: 4)
            incremental: Only index changed files (default: True)
            recreate: Recreate collection before ingesting (default: False)

        Returns:
            Dictionary with status, files_processed, and chunks_added
        """
        try:
            from .loaders import init_loader
            from .chonk import init_chonker
            from .vectors import init_vectorizer
            from .utils import construct_metadata_dict, get_git_repo_info, get_project_name

            target_collection = collection_name or db.collection_name

            loader = init_loader("kreuzberg", max_workers=max_workers)
            chunker = init_chonker("chonkie", method="semantic", chunk_size=512)
            vectorizer = init_vectorizer(
                "sentence_transformers",
                model_name=vectorizer_args.get("model_name", "minishlab/potion-multilingual-128M"),
            )

            git_repo_info = get_git_repo_info(directory)
            project_name = get_project_name(directory)
            metadata = construct_metadata_dict(
                directory, chunker, chunker.config, vectorizer, vectorizer.config, loader, loader.config, db_path, target_collection, git_repo_info=git_repo_info
            )

            from .db import MilvusLiteDB
            target_db = MilvusLiteDB(
                db_path=db_path,
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


def run_stdio(db_path: str, collection_name: str, vectorizer_args: dict):
    """Run MCP server with stdio transport."""
    mcp = create_mcp_server(db_path, collection_name, vectorizer_args)
    mcp.run(transport="stdio")


def run_http(db_path: str, collection_name: str, vectorizer_args: dict, host: str = "127.0.0.1", port: int = 8000):
    """Run MCP server with HTTP transport via SSE."""
    import uvicorn
    from fastapi import FastAPI

    mcp = create_mcp_server(db_path, collection_name, vectorizer_args, host=host, port=port)
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
    parser.add_argument("--db-path", default="rag.db", help="Path to the database file")
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
        run_http(args.db_path, args.collection_name, vectorizer_args, args.host, args.port)
    else:
        run_stdio(args.db_path, args.collection_name, vectorizer_args)


if __name__ == "__main__":
    main()