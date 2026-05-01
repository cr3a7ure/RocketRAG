from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from kreuzberg import extract_file_sync, ExtractionConfig
from .data_models import Document
from .base import BaseLoader


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "tiff", "bmp", "gif", "webp"}


class KreuzbergLoader(BaseLoader):
    name = "kreuzberg"
    supported_formats = {
        "pdf", "docx", "doc", "rtf", "txt", "epub", "md", "markdown",
        "jpg", "jpeg", "png", "tiff", "bmp", "gif", "webp",
        "xlsx", "xls", "csv", "yaml", "yml", "ods",
        "pptx", "ppt", "odp",
        "html", "xml", "mhtml",
        "py", "js", "jsx", "ts", "tsx", "css", "html", "java", "go", "rs",
        "c", "cpp", "h", "hpp", "cs", "rb", "swift", "kt", "scala", "php",
        "lua", "r", "sql", "sh", "bash", "zsh", "ps1", "vim", "elisp",
        "hs", "ml", "toml", "json", "xml", "dart", "fsharp",
        "erlang", "elixir", "julia", "perl", "objective-c", "zig", "nim",
        "crystal", "ocaml", "racket", "scheme", "lisp", "ada", "vhdl",
        "verilog", "systemverilog", "tcl", "awk", "sed", "powershell",
        "cjsx", "cxx", "hxx", "ino", "pde", "asm", "s", "S",
        "clj", "cljs", "cljc", "ex", "exs", "fs", "fsx", "fsi", "gd",
        "gitignore", "lock", "editorconfig", "env", "env-template",
        "npmrc", "prettierrc", "stylelintrc", "gitconfig",
        "cask", "dockerfile", "gemfile", "guardfile", "jenkinsfile",
        "podfile", "rakefile",
        "vue", "svelte", "astro", "blade", "twig", "latte", "liquid",
        "handlebars", "mustache", "jinja", "jinja2", "njk", "tera", "gql",
        "graphql", "prisma",
        "proto", "buf", "grpc", "openapi", "swagger",
        "inc", "macros", "bib", "tex", "latex", "cls", "sty",
        "ini", "cfg", "conf", "properties",
        "makefile", "cmake", "gradle", "maven", "ant", "build", "bazel",
        "nginx", "apache", "haproxy", "traefik",
    }

    def __init__(self, disable_ocr: bool = False, max_workers: int = 4, **kwargs: dict):
        super().__init__(**kwargs)
        self._gitignore_patterns: set = set()
        self._disable_ocr = disable_ocr
        self._config = ExtractionConfig(disable_ocr=True) if disable_ocr else None
        self._max_workers = max_workers

    def _merge_gitignore(self, parent_patterns: set, child_patterns: set) -> set:
        merged = parent_patterns.copy()
        for pattern in child_patterns:
            merged.add(pattern)
        return merged

    def _is_dir_excluded(self, dir_name: str, patterns: set) -> bool:
        import fnmatch
        for pattern in patterns:
            if pattern.endswith("/"):
                dir_pattern = pattern.rstrip("/")
                if fnmatch.fnmatch(dir_name, dir_pattern) or fnmatch.fnmatch(dir_name, f"*/{dir_pattern}"):
                    return True
            elif fnmatch.fnmatch(dir_name, pattern) or fnmatch.fnmatch(dir_name, f"*/{pattern}"):
                return True
            if pattern == "*~" and dir_name.endswith("~"):
                return True
        return False

    def _load_gitignore(self, path: Path) -> set:
        gitignore = path / ".gitignore"
        if gitignore.exists():
            patterns = set()
            for line in gitignore.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.add(line)
            return patterns
        return set()

    def _should_skip_file(self, filename: str, relative_path: str, gitignore_patterns: set) -> bool:
        import fnmatch
        full_path = str(Path(relative_path) / filename) if relative_path else filename
        for pattern in gitignore_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
            if fnmatch.fnmatch(full_path, pattern):
                return True
            if fnmatch.fnmatch(full_path, f"*/{pattern}"):
                return True
            if pattern.startswith("*.!"):
                ext = pattern[2:]
                if filename.endswith(ext):
                    return True
            if pattern == "*~" and filename.endswith("~"):
                return True
        return False

    def _language_from_extension(self, ext: str) -> str:
        ext_clean = ext.lower().lstrip(".")
        try:
            from tree_sitter_language_pack import detect_language_from_extension
            detected = detect_language_from_extension(ext_clean)
            if detected:
                return detected
        except Exception:
            pass
        fallback_map = {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "mjs": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "c": "c",
            "h": "c",
            "cpp": "cpp",
            "hpp": "cpp",
            "cc": "cpp",
            "cxx": "cpp",
            "cs": "csharp",
            "rb": "ruby",
            "swift": "swift",
            "kt": "kotlin",
            "kts": "kotlin",
            "scala": "scala",
            "php": "php",
            "lua": "lua",
            "r": "r",
            "sql": "sql",
            "sh": "bash",
            "bash": "bash",
            "zsh": "bash",
            "fish": "bash",
            "ps1": "powershell",
            "vim": "vim",
            "vimrc": "vim",
            "emacs": "elisp",
            "hs": "haskell",
            "ml": "ocaml",
            "mli": "ocaml",
            "toml": "toml",
            "json": "json",
            "xml": "xml",
            "dart": "dart",
            "fs": "fsharp",
            "fsx": "fsharp",
            "fsi": "fsharp",
            "erl": "erlang",
            "ex": "elixir",
            "exs": "elixir",
            "jl": "julia",
            "pl": "perl",
            "pm": "perl",
            "zig": "zig",
            "nim": "nim",
            "cr": "crystal",
            "ocaml": "ocaml",
            "rkt": "racket",
            "scm": "scheme",
            "lisp": "commonlisp",
            "ada": "ada",
            "adb": "ada",
            "ads": "ada",
            "vhd": "vhdl",
            "vhdl": "vhdl",
            "v": "v",
            "sv": "verilog",
            "tcl": "tcl",
            "awk": "awk",
            "sed": "sed",
            "vue": "vue",
            "svelte": "svelte",
            "astro": "astro",
            "blade": "blade",
            "latte": "blade",
            "twig": "twig",
            "liquid": "liquid",
            "hbs": "handlebars",
            "handlebars": "handlebars",
            "mustache": "mustache",
            "jinja": "jinja",
            "jinja2": "jinja",
            "njk": "njk",
            "tera": "tera",
            "gql": "graphql",
            "graphql": "graphql",
            "prisma": "prisma",
            "proto": "proto",
            "ini": "ini",
            "cfg": "ini",
            "conf": "nginx",
            "properties": "properties",
            "makefile": "make",
            "cmake": "cmake",
            "gradle": "groovy",
            "bazel": "bazel",
            "dockerfile": "dockerfile",
            "tex": "latex",
            "bib": "bibtex",
        }
        return fallback_map.get(ext_clean, ext_clean)

    def _extract_file(self, entry: Path, relative_path: str) -> Document | None:
        try:
            config = self._config
            if config is None:
                ext = entry.suffix.lstrip(".").lower()
                if ext in IMAGE_EXTENSIONS:
                    config = ExtractionConfig(disable_ocr=True)
            result = extract_file_sync(entry, config=config)
            detected_lang = result.get_detected_language()
            if not detected_lang:
                detected_lang = self._language_from_extension(entry.suffix)
            doc = Document(result.content, entry.name, language=detected_lang)
            if relative_path:
                doc.filepath = relative_path
            return doc
        except Exception:
            return None

    def _walk_dir(self, dir_path: Path, relative_path: str, patterns: set, files: list[tuple[Path, str]]):
        for entry in sorted(dir_path.iterdir()):
            if entry.is_file():
                if entry.name == ".gitignore":
                    continue
                if self._should_skip_file(entry.name, relative_path, patterns):
                    continue
                if not self._validate_file_format(entry):
                    continue
                files.append((entry, relative_path))
            elif entry.is_dir():
                subdir_ignore = entry / ".gitignore"
                child_patterns = set()
                if subdir_ignore.exists():
                    for line in subdir_ignore.read_text().splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            child_patterns.add(line)
                merged_patterns = self._merge_gitignore(patterns, child_patterns)
                subdir_relative = str(Path(relative_path) / entry.name) if relative_path else entry.name
                if self._is_dir_excluded(entry.name, merged_patterns):
                    continue
                self._walk_dir(entry, subdir_relative, merged_patterns, files)

    def load_files_from_dir(self, path: str):
        files: list[tuple[Path, str]] = []
        root_patterns = self._load_gitignore(Path(path))
        self._walk_dir(Path(path), "", root_patterns, files)

        documents = []
        skipped = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {executor.submit(self._extract_file, entry, rel_path): (entry, rel_path) for entry, rel_path in files}
            for future in as_completed(futures):
                entry, rel_path = futures[future]
                result = future.result()
                if result:
                    documents.append(result)
                else:
                    skipped.append((entry.name, entry.suffix.lstrip(".") or "no extension"))

        if skipped:
            extensions = set(ext for _, ext in skipped)
            print(f"Skipped {len(skipped)} unsupported file(s): {', '.join(sorted(extensions))}")
        return documents


def init_loader(loader: str, **kwargs: dict):
    for cls in BaseLoader.__subclasses__():
        if hasattr(cls, "name") and cls.name == loader:
            return cls(**kwargs)
    raise ValueError(
        f"Unknown loader: {loader}. Available: {[cls.name for cls in BaseLoader.__subclasses__() if hasattr(cls, 'name')]}"
    )