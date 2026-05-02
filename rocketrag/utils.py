import sys
import tty
import termios
from pathlib import Path
from datetime import datetime, timezone
from .base import BaseVectorizer, BaseChunker, BaseLoader


def get_key():
    """Get a single keypress from the user."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        key = sys.stdin.read(1)
        if key == "\x1b":  # ESC sequence
            key += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return key


def get_git_repo_info(directory: str) -> dict | None:
    """Extract git repo info from a directory. Returns None if not a git repo."""
    try:
        import subprocess
        path = Path(directory)
        git_dir = path / ".git"

        if not git_dir.exists():
            return None

        result = {
            "local_path": str(path.absolute()),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            remote = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if remote.returncode == 0:
                result["url"] = remote.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if branch.returncode == 0:
                result["branch"] = branch.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if commit.returncode == 0:
                result["commit"] = commit.stdout.strip()[:12]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return result
    except Exception:
        return None


def construct_metadata_dict(
    data_dir: str,
    chonker: BaseChunker,
    chonker_args: dict,
    vectorizer: BaseVectorizer,
    vectorizer_args: dict,
    loader: BaseLoader,
    loader_args: dict,
    db_path: str = "rag.db",
    collection_name: str = "rag",
    git_repo_info: dict | None = None,
):
    metadata = {
        "data_dir": data_dir,
        "chonker": chonker.__class__.__name__,
        "chonker_args": chonker_args,
        "vectorizer": vectorizer.__class__.__name__,
        "vectorizer_args": vectorizer_args,
        "loader": loader.__class__.__name__,
        "loader_args": loader_args,
        "db_path": db_path,
        "collection_name": collection_name,
    }
    if git_repo_info:
        metadata["git_repo"] = git_repo_info
    return metadata


def compare_medatata_dicts(db: dict, new: dict) -> dict:
    """Check if the two dictionaries have the same values and finds where they differ"""
    diff = {}
    for key in db.keys():
        if db[key] != new[key]:
            diff[key] = {
                "db": db[key],
                "new": new[key],
            }
    return diff
