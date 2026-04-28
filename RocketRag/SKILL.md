---
name: RocketRag
description: Query and manage the RocketRAG vector database for RAG workflows. USE WHEN searching documents, finding relevant chunks, listing indexed files, getting database stats, or retrieving chunks with pagination.
---

# RocketRag

Query and manage the RocketRAG vector database for retrieval-augmented generation workflows.

## Workflow Routing

| Workflow | Trigger | File |
|----------|---------|------|
| **Search** | "search", "find chunks", "query database" | `Workflows/Search.md` |
| **ListFiles** | "list files", "show files", "indexed files" | `Workflows/ListFiles.md` |
| **GetStats** | "stats", "database info", "collection stats" | `Workflows/GetStats.md` |

## Examples

**Example 1: Search for relevant content**
```
User: "Search the database for content about neural networks"
→ Uses search tool with query
→ Returns relevant chunks with scores
```

**Example 2: List all indexed files**
```
User: "What files are indexed in the database?"
→ Uses list_files tool
→ Returns all unique filenames
```

**Example 3: Get database statistics**
```
User: "Show me the database statistics"
→ Uses get_stats tool
→ Returns total chunks, files, dimension, model
```

**Example 4: Get chunks from a specific file**
```
User: "Get all chunks from the README.md file"
→ Uses get_file_chunks tool with filename
→ Returns all chunks from that file
```

**Example 5: Browse chunks with pagination**
```
User: "Show me the first 50 chunks"
→ Uses get_all_chunks tool with limit=50, offset=0
→ Returns paginated chunks
```