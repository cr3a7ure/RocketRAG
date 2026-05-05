import sys
import tty
import termios
from pathlib import Path
from datetime import datetime, timezone
from .base import BaseVectorizer, BaseChunker, BaseLoader

DEFAULT_IGNORE_DIRS = frozenset([
    "node_modules", ".git", "venv", ".venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".tox", ".nox", ".eggs", "*.egg-info", ".venv-cache",
    "env", ".env", ".cache", ".npm", ".pip",
])


def should_ignore_path(rel_path: str, ignore_patterns: frozenset[str] | None = None) -> bool:
    """Check if a path should be ignored based on ignore patterns."""
    if ignore_patterns is None:
        ignore_patterns = DEFAULT_IGNORE_DIRS

    parts = Path(rel_path).parts
    for i, part in enumerate(parts):
        if part in ignore_patterns:
            return True
        if part.endswith(".gitignore"):
            return True
    return False


def detect_git_repos(root_dir: str) -> dict[str, dict]:
    """Detect all .git directories under root_dir recursively."""
    import subprocess

    root = Path(root_dir)
    repo_map = {}

    for git_dir in root.rglob(".git"):
        if not git_dir.is_dir():
            continue

        repo_path = str(git_dir.parent.absolute())

        result = {
            "path": repo_path,
            "url": None,
            "branch": None,
            "commit": None,
        }

        try:
            remote = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
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
                cwd=repo_path,
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
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if commit.returncode == 0:
                result["commit"] = commit.stdout.strip()[:12]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        repo_map[repo_path] = result

    return repo_map


def get_repo_for_file(filepath: str, repo_map: dict[str, dict]) -> str | None:
    """Map a file path to its parent git repo's remote URL."""
    filepath_path = Path(filepath).absolute()

    for repo_path, repo_info in repo_map.items():
        try:
            repo_abs = Path(repo_path).absolute()
            if filepath_path.is_relative_to(repo_abs):
                return repo_info.get("url")
        except ValueError:
            continue

    return None


def get_project_name(directory: str) -> str | None:
    """Extract project/package name from a directory.

    Checks in order: package.json (name), pyproject.toml (project.name),
    then falls back to directory name.
    """
    import json

    path = Path(directory)

    pkg_json = path / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json) as f:
                data = json.load(f)
                if data.get("name"):
                    return data["name"]
        except (json.JSONDecodeError, OSError):
            pass

    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                if "project" in data and data["project"].get("name"):
                    return data["project"]["name"]
                if "tool" in data and data["tool"].get("poetry", {}).get("name"):
                    return data["tool"]["poetry"]["name"]
        except (json.JSONDecodeError, OSError):
            pass

    return path.name


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
