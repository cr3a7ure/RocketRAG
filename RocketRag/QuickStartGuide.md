# RocketRag Quick Start

Quick reference for using RocketRag skill.

## Tools Available

| Tool | Purpose |
|------|---------|
| `rocketrag-http_search` | Search for relevant chunks |
| `rocketrag-http_list_files` | List indexed filenames |
| `rocketrag-http_get_stats` | Get database stats |
| `rocketrag-http_get_file_chunks` | Get chunks from a file |
| `rocketrag-http_get_all_chunks` | Paginated chunk retrieval |

## Usage Examples

**Search:**
```
rocketrag-http_search(query="neural networks", top_k=5)
```

**List files:**
```
rocketrag-http_list_files()
```

**Get stats:**
```
rocketrag-http_get_stats()
```