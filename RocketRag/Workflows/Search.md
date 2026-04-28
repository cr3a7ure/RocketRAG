# Search Workflow

Search the RocketRAG vector database for relevant document chunks.

## When to Use

Use this workflow when user wants to:
- Find content related to a query
- Search for specific topics or concepts
- Retrieve relevant chunks for RAG purposes

## Steps

1. Extract the search query from user input
2. Determine top_k parameter (default: 5)
3. Call `rocketrag-http_search` tool with query and top_k
4. Return formatted results with chunk text, filename, and score

## Tool

```
tool: rocketrag-http_search
arguments:
  - name: query
    type: string
    required: true
  - name: top_k
    type: integer
    required: false
    default: 5
```