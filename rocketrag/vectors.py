from sentence_transformers import SentenceTransformer
from .base import BaseVectorizer


class SentenceTransformersVectorizer(BaseVectorizer):
    name = "sentence_transformers"

    E5_MODELS = {
        "intfloat/e5-base-v2",
        "intfloat/e5-large-v2",
        "intfloat/e5-small-v2",
    }

    def __init__(self, **kwargs):
        self.model_name = kwargs.get("model_name")
        self.model = SentenceTransformer(self.model_name)
        self.batch_size = kwargs.get("batch_size", 16)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self._is_e5 = self.model_name in self.E5_MODELS
        super().__init__(**kwargs)

    def vectorize(self, text: str):
        if self._is_e5:
            text = f"query: {text}"
        return self.model.encode(text)

    def vectorize_batch(self, texts: list[str]):
        if self._is_e5:
            texts = [f"passage: {t}" for t in texts]
        return self.model.encode(texts, batch_size=self.batch_size)


def init_vectorizer(vectorizer: str, **kwargs: dict):
    """Initialize a vectorizer by name using abstract base class discovery."""
    for cls in BaseVectorizer.__subclasses__():
        if hasattr(cls, "name") and cls.name == vectorizer:
            return cls(**kwargs)
    raise ValueError(
        f"Unknown vectorizer: {vectorizer}. Available: {[cls.name for cls in BaseVectorizer.__subclasses__() if hasattr(cls, 'name')]}"
    )
