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
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `search(query, top_k)` | Vector similarity search across all chunks |
| `list_files()` | List all indexed filenames |
| `get_file_chunks(filename)` | Get all chunks from a specific file |
| `get_stats()` | Get database statistics |
| `get_all_chunks(limit, offset)` | Paginated chunk retrieval |

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

## 📊 Performance

RocketRAG is designed for speed:

- **Document Loading**: 10x faster with Kreuzberg's optimized parsers
- **Chunking**: Semantic chunking with model2vec for superior context preservation
- **Vectorization**: Optimized batch processing with sentence-transformers
- **Retrieval**: Sub-millisecond vector search with Milvus Lite
- **Generation**: GGUF quantization for 4x faster inference

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
