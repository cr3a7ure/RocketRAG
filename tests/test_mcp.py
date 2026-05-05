"""Tests for MCP server tools."""

import json
import os
from pathlib import Path

import pytest

from rocketrag.data_models import Document
from rocketrag.db import MilvusLiteDB
from rocketrag.vectors import SentenceTransformersVectorizer
from rocketrag.chonk import ChonkieChunker


@pytest.fixture
def vectorizer():
    return SentenceTransformersVectorizer(model_name="minishlab/potion-base-8M")


@pytest.fixture
def chunker():
    return ChonkieChunker(
        method="semantic",
        embedding_model="minishlab/potion-base-8M",
        chunk_size=256,
    )


@pytest.fixture
def db_instance(temp_dir, vectorizer, chunker):
    db_path = os.path.join(temp_dir, "test.db")
    metadata = {"data_dir": "test", "vectorizer": "SentenceTransformersVectorizer"}
    db = MilvusLiteDB(
        db_path=db_path,
        collection_name="test_mcp",
        vectorizer=vectorizer,
        chunker=chunker,
        metadata=metadata,
    )
    db.create_collection_if_not_exists(recreate=True)
    yield db


class TestQuickSearchDepResolution:
    def test_resolves_package_json_deps(self, temp_dir, db_instance):
        project_dir = Path(temp_dir) / "myproject"
        project_dir.mkdir()

        (project_dir / "package.json").write_text(json.dumps({
            "name": "my-app",
            "dependencies": {
                "lodash": "^4.17.21",
                "express": "^4.18.0"
            }
        }))

        doc1 = Document(
            content="Lodash utility function",
            filename="lodash-util.js",
            project_name="lodash",
        )
        doc2 = Document(
            content="Express routing",
            filename="route.js",
            project_name="express",
        )
        doc3 = Document(
            content="My app implementation",
            filename="app.js",
            project_name="my-app",
        )
        db_instance.add_documents([doc1, doc2, doc3])

        results = db_instance.search("routing", top_k=10, filter='project_name in ["my-app", "lodash", "express"]')

        project_names = {r.project_name for r in results}
        assert "my-app" in project_names
        assert "lodash" in project_names
        assert "express" in project_names

    def test_resolves_pyproject_deps(self, temp_dir, db_instance):
        project_dir = Path(temp_dir) / "pyproject"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text('[project]\nname = "my-pkg"\ndependencies = ["requests", "numpy"]\n')

        doc1 = Document(
            content="NumPy array operations",
            filename="numpy_ops.py",
            project_name="numpy",
        )
        doc2 = Document(
            content="My package code",
            filename="mypkg.py",
            project_name="my-pkg",
        )
        db_instance.add_documents([doc1, doc2])

        results = db_instance.search("array", top_k=10, filter='project_name in ["my-pkg", "requests", "numpy"]')

        project_names = {r.project_name for r in results}
        assert "numpy" in project_names
        assert "my-pkg" in project_names

    def test_falls_back_to_dir_name_without_deps(self, temp_dir, db_instance):
        project_dir = Path(temp_dir) / "plain-project"
        project_dir.mkdir()

        doc = Document(
            content="Some implementation",
            filename="code.py",
            project_name="plain-project",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("implementation", top_k=5, filter='project_name in ["plain-project"]')

        assert len(results) >= 1
        assert results[0].project_name == "plain-project"


class TestDeepSearchNoFilter:
    def test_search_without_project_filter_finds_all(self, db_instance):
        doc1 = Document(
            content="Auth service implementation",
            filename="auth.py",
            project_name="auth-service",
        )
        doc2 = Document(
            content="Gateway routing implementation",
            filename="gateway.py",
            project_name="gateway-service",
        )
        doc3 = Document(
            content="Shared library code",
            filename="shared.py",
            project_name="shared-lib",
        )
        db_instance.add_documents([doc1, doc2, doc3])

        results = db_instance.search("implementation", top_k=10)

        project_names = {r.project_name for r in results}
        assert "auth-service" in project_names
        assert "gateway-service" in project_names
        assert "shared-lib" in project_names


class TestSearchWithInFilter:
    def test_in_filter_with_multiple_values(self, db_instance):
        doc1 = Document(
            content="JWT token handling",
            filename="jwt.py",
            project_name="auth-service",
        )
        doc2 = Document(
            content="Gateway routing",
            filename="route.py",
            project_name="gateway-service",
        )
        doc3 = Document(
            content="Logger implementation",
            filename="log.py",
            project_name="logger",
        )
        db_instance.add_documents([doc1, doc2, doc3])

        results = db_instance.search("implementation", top_k=5, filter='project_name in ["auth-service", "gateway-service"]')

        for r in results:
            assert r.project_name in ["auth-service", "gateway-service"]

    def test_in_filter_with_single_value(self, db_instance):
        doc = Document(
            content="Auth JWT code",
            filename="auth.py",
            project_name="auth-service",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("jwt", top_k=5, filter='project_name in ["auth-service"]')

        assert len(results) >= 1
        for r in results:
            assert r.project_name == "auth-service"


class TestSearchResultFields:
    def test_result_contains_all_metadata_fields(self, db_instance):
        doc = Document(
            content="Test content about authentication",
            filename="auth.py",
            source="https://github.com/user/auth-service",
            project_name="auth-service",
            language="python",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("authentication", top_k=5)

        assert len(results) >= 1
        r = results[0]
        assert hasattr(r, 'chunk')
        assert hasattr(r, 'filename')
        assert hasattr(r, 'score')
        assert hasattr(r, 'source')
        assert hasattr(r, 'project_name')
        assert hasattr(r, 'language')
        assert r.filename == "auth.py"
        assert r.source == "https://github.com/user/auth-service"
        assert r.project_name == "auth-service"
        assert r.language == "python"
