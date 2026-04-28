from pathlib import Path
from kreuzberg import extract_file_sync
from .data_models import Document
from .base import BaseLoader


class KreuzbergLoader(BaseLoader):
    name = "kreuzberg"
    supported_formats = {
        # Documents
        "pdf", "docx", "doc", "rtf", "txt", "epub", "md", "markdown",
        # Images
        "jpg", "jpeg", "png", "tiff", "bmp", "gif", "webp",
        # Spreadsheets
        "xlsx", "xls", "csv", "yaml", "yml", "ods",
        # Presentations
        "pptx", "ppt", "odp",
        # Web
        "html", "xml", "mhtml",
        # Code
        "py", "js", "jsx", "ts", "tsx", "css",
    }

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)

    def load_files_from_dir(self, path: str):
        documents: list[Document] = []
        skipped_files: list[tuple[str, str]] = []
        for file in Path(path).iterdir():
            if file.is_file(): 
                if not self._validate_file_format(file):
                    skipped_files.append((file.name, file.suffix.lstrip(".")))
                    continue
                
                try:
                    content = extract_file_sync(file).content
                    documents.append(Document(content, file.name))
                except Exception:
                    skipped_files.append((file.name, file.suffix.lstrip(".") or "no extension"))
                    continue
        
        if skipped_files:
            extensions = set(ext for _, ext in skipped_files)
            print(f"Skipped {len(skipped_files)} unsupported file(s): {', '.join(sorted(extensions))}")
        
        return documents


def init_loader(loader: str, **kwargs: dict):
    """Initialize a loader by name using abstract base class discovery."""
    for cls in BaseLoader.__subclasses__():
        if hasattr(cls, "name") and cls.name == loader:
            return cls(**kwargs)
    raise ValueError(
        f"Unknown loader: {loader}. Available: {[cls.name for cls in BaseLoader.__subclasses__() if hasattr(cls, 'name')]}"
    )
