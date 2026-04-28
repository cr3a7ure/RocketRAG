# GetStats Workflow

Get database statistics from the RocketRAG vector database.

## When to Use

Use this workflow when user wants to:
- Get database statistics
- Check collection info
- Verify database state

## Steps

1. Call `rocketrag-http_get_stats` tool with no arguments
2. Return formatted statistics (total_chunks, unique_files, dimension, vectorizer_model)

## Tool

```
tool: rocketrag-http_get_stats
```