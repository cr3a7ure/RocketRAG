# ListFiles Workflow

List all unique filenames indexed in the RocketRAG database.

## When to Use

Use this workflow when user wants to:
- See what files are indexed
- Check which documents are available
- Verify indexing status

## Steps

1. Call `rocketrag-http_list_files` tool with no arguments
2. Return formatted list of filenames

## Tool

```
tool: rocketrag-http_list_files
```