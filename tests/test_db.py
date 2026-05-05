"""Tests for the database module."""

import os
import tempfile
import shutil
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
        collection_name="test_source",
        vectorizer=vectorizer,
        chunker=chunker,
        metadata=metadata,
    )
    db.create_collection_if_not_exists(recreate=True)
    yield db


class TestSourceField:
    def test_add_document_with_source(self, db_instance):
        doc = Document(
            content="Test content about authentication and JWT tokens",
            filename="auth.py",
            source="https://github.com/user/auth-service",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("jwt", top_k=5)

        assert len(results) >= 1
        assert results[0].source == "https://github.com/user/auth-service"

    def test_add_document_without_source(self, db_instance):
        doc = Document(
            content="Test content about testing frameworks",
            filename="test.py",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("testing", top_k=5)

        assert len(results) >= 1
        assert results[0].source == ""

    def test_source_in_search_results(self, db_instance):
        doc1 = Document(
            content="Auth service implementation",
            filename="auth.py",
            source="https://github.com/user/auth",
        )
        doc2 = Document(
            content="API gateway implementation",
            filename="gateway.py",
            source="https://github.com/user/gateway",
        )
        db_instance.add_documents([doc1, doc2])

        results = db_instance.search("implementation", top_k=5)

        sources = {r.source for r in results}
        assert "https://github.com/user/auth" in sources
        assert "https://github.com/user/gateway" in sources


class TestSearchWithFilter:
    def test_search_with_source_filter(self, db_instance):
        doc1 = Document(
            content="JWT token validation code",
            filename="jwt.py",
            source="https://github.com/user/auth",
        )
        doc2 = Document(
            content="Gateway routing code",
            filename="route.py",
            source="https://github.com/user/gateway",
        )
        db_instance.add_documents([doc1, doc2])

        results = db_instance.search("code", top_k=5, filter='source == "https://github.com/user/auth"')

        assert len(results) >= 1
        for r in results:
            assert r.source == "https://github.com/user/auth"

    def test_search_without_filter_returns_all(self, db_instance):
        doc1 = Document(
            content="JWT token validation",
            filename="jwt.py",
            source="https://github.com/user/auth",
        )
        doc2 = Document(
            content="Gateway routing",
            filename="route.py",
            source="https://github.com/user/gateway",
        )
        db_instance.add_documents([doc1, doc2])

        results = db_instance.search("code", top_k=5)

        sources = {r.source for r in results}
        assert len(sources) == 2


class TestProjectNameField:
    def test_add_document_with_project_name(self, db_instance):
        doc = Document(
            content="Auth service JWT implementation",
            filename="auth.py",
            project_name="auth-service",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("jwt", top_k=5)

        assert len(results) >= 1
        assert results[0].project_name == "auth-service"

    def test_add_document_without_project_name(self, db_instance):
        doc = Document(
            content="Testing framework content",
            filename="test.py",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("testing", top_k=5)

        assert len(results) >= 1
        assert results[0].project_name == ""

    def test_search_with_project_name_filter(self, db_instance):
        doc1 = Document(
            content="JWT token auth",
            filename="jwt.py",
            project_name="auth-service",
        )
        doc2 = Document(
            content="Gateway routing code",
            filename="route.py",
            project_name="gateway-service",
        )
        db_instance.add_documents([doc1, doc2])

        results = db_instance.search("code", top_k=5, filter='project_name == "auth-service"')

        assert len(results) >= 1
        for r in results:
            assert r.project_name == "auth-service"

    def test_project_name_and_source_together(self, db_instance):
        doc = Document(
            content="OAuth implementation",
            filename="oauth.py",
            source="https://github.com/user/auth",
            project_name="auth-service",
        )
        db_instance.add_documents([doc])

        results = db_instance.search("oauth", top_k=5)

        assert len(results) >= 1
        assert results[0].source == "https://github.com/user/auth"
        assert results[0].project_name == "auth-service"