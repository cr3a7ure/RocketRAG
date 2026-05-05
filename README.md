# 🚀 RocketRAG

**Fast, efficient, minimal, extendible and elegant RAG system**

RocketRAG is a high-performance Retrieval-Augmented Generation (RAG) system designed with a focus on speed, simplicity, and extensibility. Built on top of state-of-the-art libraries, it provides both CLI and web server capabilities for seamless integration into any workflow.

<https://github.com/user-attachments/assets/1bd7cc50-9eac-4402-80bd-42933ac35ca3>

## 🎯 Mission

RocketRAG aims to be the **fastest and most efficient RAG library** while maintaining:

- **Minimal footprint** - Clean, lightweight codebase
- **Maximum extensibility** - Pluggable architecture for all components
- **Peak performance** - Leveraging the best-in-class libraries
- **Ease of use** - Simple CLI and API interfaces

## ⚡ Performance-First Architecture

RocketRAG is built on top of cutting-edge, performance-optimized libraries:

- **[Chonkie](https://github.com/bhavnicksm/chonkie)** - Ultra-fast semantic chunking with model2vec
- **[Kreuzberg](https://github.com/mixedbread-ai/kreuzberg)** - Lightning-fast document loading and processing
- **[llama-cpp-python](https://github.com/abetlen/llama-cpp-python)** - Optimized LLM inference with GGUF support
- **[Milvus Lite](https://github.com/milvus-io/milvus-lite)** - High-performance vector database
- **[Sentence Transformers](https://github.com/UKPLab/sentence-transformers)** - State-of-the-art embeddings

## 🚀 Quick Start

### Installation

#### Using pip

```bash
pip install rocketrag
```

#### Using uvx (recommended for CLI usage)

```bash
# Run directly without installation
uvx rocketrag --help

# Or install globally
uvx install rocketrag
```

### Basic Usage

```python
from rocketrag import RocketRAG

rag = RocketRAG("./data") # Path do your data (supports PDF, TXT, MD, etc.)
rag.prepare() # Construct vector database

# Ask questions
answer, sources = rag.ask("What is the main topic of the documents?")
print(answer)
```

### CLI Usage

```bash
# Prepare documents from a directory
rocketrag prepare --data-dir ./documents

# Check files without indexing (dry-run)
rocketrag prepare --data-dir ./documents --dry-run

# Incremental index (only changed files)
rocketrag prepare --data-dir ./documents --incremental

# Search the vector database with metadata filtering
rocketrag search "jwt" --collection-name localdev --top-k 5
rocketrag search "auth" --filter 'source like "%auth%"' --top-k 5

# List indexed files
rocketrag list-files --db-path rag.db

# Show database statistics
rocketrag stats --collection-name localdev

# Ingest a directory (with auto git detection)
rocketrag ingest ./company --collection-name localdev --incremental

# Ask questions via CLI
rocketrag ask "What are the key findings?"

# Start web server
rocketrag server --port 8000

# Start MCP server for AI agent integration
rocketrag mcp-server
```

#### Using uvx (no installation required)

```bash
# Same commands work with uvx
uvx rocketrag prepare --data-dir ./documents
uvx rocketrag ask "What are the key findings?"
uvx rocketrag server --port 8000

# Run as module
uvx --from rocketrag python -m rocketrag --help
```

## 🏗️ Architecture

RocketRAG follows a modular, plugin-based architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Document      │    │    Chunking     │    │   Vectorization │
│   Loaders       │───▶│   (Chonkie)     │───▶│ (SentenceTransf)│
│  (Kreuzberg)    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐             │
│      LLM        │    │   Vector DB     │◀────────────┘
│ (llama-cpp-py)  │◀───│ (Milvus Lite)   │
│                 │    │                 │
└─────────────────┘    └─────────────────┘
```

### Core Components

- **BaseLoader**: Pluggable document loading (PDF, TXT, MD, YAML, code files, etc.)
- **BaseChunker**: Configurable chunking strategies (semantic, recursive, etc.)
- **BaseVectorizer**: Flexible embedding models
- **BaseLLM**: Swappable language models
- **MilvusLiteDB**: High-performance vector storage and retrieval

## 🔧 Configuration

### Custom Components

```python
from rocketrag import RocketRAG
from rocketrag.vectors import SentenceTransformersVectorizer
from rocketrag.chonk import ChonkieChunker
from rocketrag.llm import LLamaLLM
from rocketrag.loaders import KreuzbergLoader

# Configure high-performance components
vectorizer = SentenceTransformersVectorizer(
    model_name="minishlab/potion-multilingual-128M"  # Fast multilingual model
)

chunker = ChonkieChunker(
    method="semantic",  # Semantic chunking for better context
    embedding_model="minishlab/potion-multilingual-128M",
    chunk_size=512
)

llm = LLamaLLM(
    repo_id="unsloth/gemma-3n-E2B-it-GGUF",
    filename="*Q8_0.gguf"  # Quantized for speed
)

loader = KreuzbergLoader()  # Ultra-fast document processing

rag = RocketRAG(
    vectorizer=vectorizer,
    chunker=chunker,
    llm=llm,
    loader=loader
)
```

### CLI Configuration

```bash
# Custom chunking strategy
rocketrag prepare \
  --chonker chonkie \
  --chonker-args '{"method": "semantic", "chunk_size": 512}' \
  --vectorizer-args '{"model_name": "all-MiniLM-L6-v2"}'

# Custom LLM for inference
rocketrag ask "Your question" \
  --repo-id "microsoft/DialoGPT-medium" \
  --filename "*.gguf"
```

### E5 Embedding Model

The [intfloat/e5](https://huggingface.co/intfloat/e5-base-v2) models provide high-quality embeddings for technical content. RocketRAG automatically handles the required `"query: "` and `"passage: "` prefixes:

```python
from rocketrag import RocketRAG
from rocketrag.vectors import SentenceTransformersVectorizer
from rocketrag.chonk import ChonkieChunker
from rocketrag.loaders import KreuzbergLoader

vectorizer = SentenceTransformersVectorizer(
    model_name="intfloat/e5-base-v2"  # 768 dimensions, strong on technical content
)

chunker = ChonkieChunker(
    method="semantic",
    embedding_model="intfloat/e5-base-v2",
    chunk_size=512,
    threshold=0.3
)

loader = KreuzbergLoader()

rag = RocketRAG(
    data_dir="./data",
    db_path="e5_rag.db",
    collection_name="e5_docs",
    vectorizer=vectorizer,
    chunker=chunker,
    loader=loader,
)

rag.prepare()
answer, sources = rag.ask("What is the main topic?")
```

```bash
# Or via CLI with e5-base-v2
rocketrag prepare \
  --data-dir ./documents \
  --vectorizer-args '{"model_name": "intfloat/e5-base-v2"}' \
  --chonker-args '{"method": "semantic", "chunk_size": 512}'
```

### Qwen Embedding Model

The [Qwen text-embedding-v4](https://help.aliyun.com/document_detail/2712512.html) model from Alibaba Cloud provides high-quality 1024-dimensional embeddings via the DashScope API:

```python
import os
from rocketrag import RocketRAG
from rocketrag.vectors import QwenEmbeddingVectorizer
from rocketrag.chonk import ChonkieChunker
from rocketrag.loaders import KreuzbergLoader

os.environ["DASHSCOPE_API_KEY"] = "your-api-key"

vectorizer = QwenEmbeddingVectorizer(
    model_name="text-embedding-v4",  # 1024 dimensions
)

chunker = ChonkieChunker(
    method="semantic",
    embedding_model="minishlab/potion-multilingual-128M",
    chunk_size=512,
    threshold=0.3
)

loader = KreuzbergLoader()

rag = RocketRAG(
    data_dir="./data",
    db_path="qwen_rag.db",
    collection_name="qwen_docs",
    vectorizer=vectorizer,
    chunker=chunker,
    loader=loader,
)

rag.prepare()
answer, sources = rag.ask("What is the main topic?")
```

```bash
# Or via CLI with Qwen embeddings
export DASHSCOPE_API_KEY="your-api-key"
rocketrag prepare \
  --data-dir ./documents \
  --vectorizer-args '{"model_name": "text-embedding-v4"}' \
  --chonker-args '{"method": "semantic", "chunk_size": 512}'
```

## 🌐 Web Server

RocketRAG includes a FastAPI-based web server with OpenAI-compatible endpoints:

```bash
# Start server
rocketrag server --port 8000 --host 0.0.0.0
```

### API Endpoints

- `GET /` - Interactive web interface
- `POST /ask` - Question answering
- `POST /ask/stream` - Streaming responses
- `GET /chat` - Chat interface
- `GET /browse` - Document browser
- `GET /visualize` - Vector visualization
- `GET /health` - Health check

### Example API Usage

```python
import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={"question": "What are the main findings?"}
)

result = response.json()
print(result["answer"])
print(result["sources"])
```

## 🎨 Features

### Core Features

- ⚡ **Ultra-fast document processing** with Kreuzberg
- 🧠 **Semantic chunking** with Chonkie and model2vec
- 🔍 **High-performance vector search** with Milvus Lite
- 🤖 **Optimized LLM inference** with llama-cpp-python
- 📊 **Rich CLI interface** with progress bars and formatting
- 🌐 **Web server** with interactive UI
- 🔌 **Pluggable architecture** for easy customization

### Advanced Features

- 📈 **Vector visualization** for debugging and analysis
- 📚 **Document browsing** interface
- 💬 **Streaming responses** for real-time interaction
- 🔄 **Batch processing** for large document sets
- 📝 **Metadata preservation** throughout the pipeline
- 🎯 **Context-aware chunking** for better retrieval
- 🔌 **MCP server** for AI agent integration
- 🗂️ **Multi-repo source tracking** with git remote URL metadata
- 🚫 **Automatic directory filtering** (skips node_modules, dist, venv, .git, etc.)
- 🔍 **Metadata filtering** in search results
- 🎯 **Project-aware search** (quick_search auto-resolves dependencies from package.json/pyproject.toml)

## 🤖 MCP Server

RocketRAG includes an MCP (Model Context Protocol) server for integration with AI agents. Supports both **stdio** (local) and **HTTP** (remote) transports.

### Stdio Transport (Local)

```bash
# Start MCP server with stdio transport
rocketrag mcp-server

# Or with custom settings
rocketrag mcp-server --db-path ./rag.db --collection-name docs
```

### HTTP Transport (Remote)

```bash
# Start MCP server with HTTP transport on custom port
rocketrag mcp-server --transport http --host 0.0.0.0 --port 8000 --db-path ./rag.db --collection-name docs

# With e5-base-v2 embeddings
rocketrag mcp-server --transport http --host 0.0.0.0 --port 8000 \
  --db-path ./rag.db \
  --collection-name docs \
  --vectorizer-args '{"model_name": "intfloat/e5-base-v2"}'

# With Qwen text-embedding-v4 (1024 dimensions)
export DASHSCOPE_API_KEY="your-api-key"
rocketrag mcp-server --transport http --host 0.0.0.0 --port 8000 \
  --db-path ./rag.db \
  --collection-name docs \
  --vectorizer-args '{"model_name": "text-embedding-v4"}'
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `quick_search(project_path, query, top_k)` | Project-aware search (auto-resolves deps from package.json/pyproject.toml) |
| `deep_search(query, top_k, filter)` | Full search without project filtering - exploratory mode |
| `search_all(query, top_k, filter)` | Search all collections |
| `list_files()` | List all indexed filenames |
| `get_file_chunks(filename)` | Get all chunks from a specific file |
| `get_stats()` | Get database statistics |
| `get_all_chunks(limit, offset)` | Paginated chunk retrieval |
| `ingest_directory(directory, collection_name, db_path)` | Ingest a directory (optionally to separate DB) |

### HTTP Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service info and available tools |
| `GET /health` | Health check |
| `/mcp/sse` | MCP SSE endpoint for tool calls |
| `/mcp/messages` | MCP messages endpoint |

### MCP Client Configuration

**Claude Desktop (Stdio):**

```json
{
  "mcpServers": {
    "rocketrag": {
      "command": "uvx",
      "args": ["rocketrag", "mcp-server"]
    }
  }
}
```

**Claude Desktop (HTTP Remote):**

```json
{
  "mcpServers": {
    "rocketrag": {
      "type": "http",
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

**OpenCode:**

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "rocketrag-stdio": {
      "type": "stdio",
      "command": "uvx",
      "args": ["rocketrag", "mcp-server"]
    },
    "rocketrag-http": {
      "type": "remote",
      "url": "http://localhost:8000/mcp/sse",
      "enabled": false
    }
  }
}
```

**OpenCode MCP Tools:**

```yaml
# .opencode/agents/default/tools.yaml
tools:
  - name: rocketrag-search
    description: Search the RocketRAG vector database for relevant chunks
    arguments:
      - name: query
        type: string
        required: true
      - name: top_k
        type: integer
        required: false
        default: 5

  - name: rocketrag-list-files
    description: List all indexed filenames in the database

  - name: rocketrag-get-file-chunks
    description: Get all chunks from a specific file
    arguments:
      - name: filename
        type: string
        required: true

  - name: rocketrag-stats
    description: Get database statistics (chunks, files, dimension)

  - name: rocketrag-get-all-chunks
    description: Get all chunks with pagination
    arguments:
      - name: limit
        type: integer
        required: false
        default: 100
      - name: offset
        type: integer
        required: false
        default: 0

  - name: rocketrag-ingest
    description: Ingest a directory into the vector database
    arguments:
      - name: directory
        type: string
        required: true
        description: Path to directory to ingest
      - name: collection_name
        type: string
        required: false
        default: localdev
        description: Collection name (default: localdev)
      - name: max_workers
        type: integer
        required: false
        default: 4
        description: Parallel workers for extraction
      - name: incremental
        type: boolean
        required: false
        default: true
        description: Only index changed files
```

## 🛠️ Development

### Installation for Development

```bash
git clone https://github.com/yourusername/rocketrag.git
cd rocketrag
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
ruff check .
ruff format .
```

## 🐳 Docker Deployment

Deploy RocketRAG using Docker for consistent environments across systems.

### Quick Start

```bash
# Build and start all services
docker-compose up -d

# Or build manually
docker build -t rocketrag .
docker run -p 8000:8000 -v ./data:/data rocketrag server --port 8000
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `rocketrag` | 8000 | Web server with REST API |
| `rocketrag-mcp` | 8001 | MCP server for AI agent integration |

### Data Persistence

Mount volumes to persist data:

```yaml
volumes:
  - ./data:/data        # Document directory
  - ./rag.db:/data/rag.db  # Vector database
```

### Environment Variables

```bash
PYTHONUNBUFFERED=1  # Ensure output is not buffered
```

### Examples

```bash
# Start web server
docker-compose up rocketrag

# Start MCP server only
docker-compose up rocketrag-mcp

# Ingest a directory via MCP
# Use ingest_directory tool with directory="/data/my-project"
```

### Docker Ingest Script

Use the `ingest-docker.sh` script to ingest directories via Docker:

```bash
# Build slim image (one-time, ~30s vs ~5min for full build with llama.cpp)
docker build -f Dockerfile.slim -t rocketrag .

# Basic usage (CPU-optimized, uses potion model)
./ingest-docker.sh ./my-project

# Custom DB and collection
./ingest-docker.sh ./docs --db-path project.db --collection myapp

# With e5 model and GPU support (for faster vectorization)
./ingest-docker.sh ./repo --collection tech --model intfloat/e5-base-v2 --gpu

# Incremental mode (skip unchanged files)
./ingest-docker.sh ./repo --incremental

# Full options
./ingest-docker.sh ./docs \
  --db-path rag.db \
  --collection my-collection \
  --model intfloat/e5-base-v2 \
  --max-workers 8 \
  --incremental \
  --gpu
```

#### GPU Support

When using `--gpu`, Docker passes GPU access to the container via `--gpus all`. This enables:

- **CUDA GPU acceleration** for vectorization models (e5-base-v2, e5-large-v2)
- **Significantly faster embedding** on large document sets
- **Better CPU utilization** since GPU handles vectorization

**Requirements:**
- NVIDIA GPU with CUDA drivers installed
- [`nvidia-container-toolkit`](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) configured

**Model recommendations:**

| Model | CPU Speed | GPU Needed? | Use Case |
|-------|-----------|-------------|----------|
| `minishlab/potion-multilingual-128M` | Fast | No | Default, CPU-only Docker |
| `intfloat/e5-base-v2` | Slow on CPU | Yes (recommended) | Higher quality embeddings |
| `intfloat/e5-small-v2` | Moderate | Recommended | Lightweight GPU alternative |

> **Note:** The script mounts the parent directory of `--db-path` as a Docker volume, so `rag.db` becomes a directory mount point. To run subsequent commands (stats, search, etc.), mount the same directory:
>
> ```bash
> # Run stats with volume mount
> docker run --rm -v "$(pwd):/data" -w /data rocketrag \
>   rocketrag stats --db-path rag.db --collection-name my-collection
>
> # Search
> docker run --rm -v "$(pwd):/data" -w /data rocketrag \
>   rocketrag search "your query" --db-path rag.db --collection-name my-collection
> ```

## 📊 Performance

RocketRAG is designed for speed:

- **Document Loading**: 10x faster with Kreuzberg's optimized parsers, parallel extraction with configurable workers
- **Chunking**: Semantic chunking with model2vec for superior context preservation
- **Vectorization**: Optimized batch processing with sentence-transformers
- **Retrieval**: Sub-millisecond vector search with Milvus Lite
- **Generation**: GGUF quantization for 4x faster inference
- **Dry-run**: Check files before indexing to catch problems early
- **Incremental Indexing**: Skip unchanged files using mtime/size tracking
- **Git Source Tracking**: Auto-captures repo URL, branch, and commit for traceability

## 🤝 Contributing

We welcome contributions! RocketRAG's modular architecture makes it easy to:

- Add new document loaders
- Implement custom chunking strategies
- Integrate different embedding models
- Support additional LLM backends
- Enhance the web interface

## 🙏 Acknowledgments

RocketRAG builds upon the excellent work of:

- [Chonkie](https://github.com/bhavnicksm/chonkie) for semantic chunking
- [Kreuzberg](https://github.com/mixedbread-ai/kreuzberg) for document processing
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) for LLM inference
- [Milvus](https://github.com/milvus-io/milvus-lite) for vector storage
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers) for embeddings
