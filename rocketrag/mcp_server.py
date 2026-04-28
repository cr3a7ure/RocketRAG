from mcp.server.fastmcp import FastMCP
from .db import MilvusLiteDB
from .vectors import init_vectorizer


def create_mcp_server(db_path: str, collection_name: str, vectorizer_args: dict):
    """Create an MCP server for querying the RocketRAG database."""
    vectorizer = init_vectorizer("sentence_transformers", **vectorizer_args)

    db = MilvusLiteDB(
        db_path=db_path,
        collection_name=collection_name,
        vectorizer=vectorizer,
    )

    mcp = FastMCP("RocketRAG Query Server")

    @mcp.tool()
    def search(query: str, top_k: int = 5) -> list[dict]:
        """Search the database for relevant chunks.

        Args:
            query: The search query text
            top_k: Number of results to return (default: 5)

        Returns:
            List of search results with chunk text, filename, and score
        """
        results = db.search(query, top_k=top_k)
        return [
            {
                "chunk": r.chunk,
                "filename": r.filename,
                "score": r.score,
            }
            for r in results
        ]

    @mcp.tool()
    def list_files() -> list[str]:
        """List all unique filenames indexed in the database.

        Returns:
            List of unique filenames
        """
        return db.get_unique_filenames()

    @mcp.tool()
    def get_file_chunks(filename: str) -> list[dict]:
        """Get all chunks from a specific file.

        Args:
            filename: The filename to retrieve chunks for

        Returns:
            List of chunks with text and id
        """
        results = db.get_vectors_by_filename(filename)
        return [
            {
                "id": r["id"],
                "text": r["text"],
            }
            for r in results
        ]

    @mcp.tool()
    def get_stats() -> dict:
        """Get database statistics.

        Returns:
            Dictionary with total_chunks, unique_files, dimension, and vectorizer_model
        """
        total = db.get_total_count()
        files = db.get_unique_filenames()
        metadata = db.get_collection_metadata()

        return {
            "total_chunks": total,
            "unique_files": len(files),
            "dimension": db.dimension,
            "vectorizer_model": metadata.get("vectorizer_args", {}).get("model_name", "unknown"),
        }

    @mcp.tool()
    def get_all_chunks(limit: int = 100, offset: int = 0) -> list[dict]:
        """Get all chunks with pagination.

        Args:
            limit: Maximum number of chunks to return (default: 100)
            offset: Number of chunks to skip (default: 0)

        Returns:
            List of chunks with text and filename
        """
        results = db.get_all_records(limit=limit, offset=offset)
        return [
            {
                "id": r["id"],
                "text": r["text"],
                "filename": r["filename"],
            }
            for r in results
        ]

    return mcp


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

    args = parser.parse_args()

    vectorizer_args = json.loads(args.vectorizer_args)
    mcp = create_mcp_server(args.db_path, args.collection_name, vectorizer_args)

    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()