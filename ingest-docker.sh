#!/bin/bash
set -e

# Default values
DB_PATH="rag.db"
COLLECTION="rag"
MODEL="minishlab/potion-multilingual-128M"
MAX_WORKERS=4
INCREMENTAL="false"

usage() {
    echo "Usage: $0 <directory> [--db-path <path>] [--collection <name>] [--model <model>] [--max-workers <n>] [--incremental]"
    echo ""
    echo "Arguments:"
    echo "  directory          Directory to ingest (required)"
    echo "  --db-path           Database file path (default: rag.db)"
    echo "  --collection        Collection name (default: rag)"
    echo "  --model             Vectorizer model (default: minishlab/potion-multilingual-128M)"
    echo "  --max-workers       Parallel workers (default: 4)"
    echo "  --incremental       Enable incremental mode (default: false)"
    echo ""
    echo "Examples:"
    echo "  $0 ./my-project --db-path project.db --collection myapp"
    echo "  $0 /data/docs --collection tech-docs --model intfloat/e5-base-v2"
    echo ""
    echo "  # Build slim image first (skip this if already built):"
    echo "  docker build -f Dockerfile.slim -t rocketrag ."
    echo ""
    echo "  # Ingest current directory (mounts as volume in Docker):"
    echo "  $0 ."
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

DIRECTORY="$1"
shift

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --db-path)
            DB_PATH="$2"
            shift 2
            ;;
        --collection)
            COLLECTION="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --max-workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        --incremental)
            INCREMENTAL="true"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [ -z "$DIRECTORY" ]; then
    echo "Error: directory is required"
    usage
fi

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: directory not found: $DIRECTORY"
    exit 1
fi

# Get absolute path
DIR_ABS=$(realpath "$DIRECTORY")
DIR_NAME=$(basename "$DIR_ABS")

echo "=========================================="
echo "  RocketRAG Docker Ingest"
echo "=========================================="
echo "  Directory:    $DIR_ABS"
echo "  DB Path:      $DB_PATH"
echo "  Collection:   $COLLECTION"
echo "  Model:        $MODEL"
echo "  Workers:      $MAX_WORKERS"
echo "  Incremental:  $INCREMENTAL"
echo "=========================================="
echo ""

CMD="python -m rocketrag prepare '/data/$DIR_NAME' --db-path '$DB_PATH' --collection-name '$COLLECTION' --vectorizer-args '{\"model_name\": \"$MODEL\"}' --max-workers $MAX_WORKERS"

if [ "$INCREMENTAL" = "true" ]; then
    CMD="$CMD --incremental"
fi

# Run in docker
docker run --rm \
    --entrypoint sh \
    -v "$(pwd)/$DB_PATH:/data/$DB_PATH" \
    -v "$DIR_ABS:/data/$DIR_NAME:ro" \
    -w /data \
    rocketrag \
    -c "$CMD"

echo ""
echo "Done! Data stored in: $(pwd)/$DB_PATH"
echo "Collection: $COLLECTION"