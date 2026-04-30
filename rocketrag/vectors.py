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


class QwenEmbeddingVectorizer(BaseVectorizer):
    name = "qwen"
    dimension = 1024

    QWEN_MODELS = {
        "text-embedding-v4",
        "text-embedding-v4-sft",
    }

    def __init__(self, **kwargs):
        self.model_name = kwargs.get("model_name", "text-embedding-v4")
        self.batch_size = kwargs.get("batch_size", 16)
        self._api_key = kwargs.get("api_key") or kwargs.get("DASHSCOPE_API_KEY")
        self._base_url = kwargs.get(
            "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self._client = None
        super().__init__(**kwargs)

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "Please install the openai package: pip install openai"
                )

            if not self._api_key:
                raise ValueError(
                    "DASHSCOPE_API_KEY environment variable or api_key argument is required. "
                    "Get your API key at https://dashscope.console.aliyun.com/"
                )

            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    def vectorize(self, text: str):
        client = self._get_client()
        response = client.embeddings.create(
            model=self.model_name,
            input=text,
        )
        return response.data[0].embedding

    def vectorize_batch(self, texts: list[str]):
        client = self._get_client()
        response = client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]


def init_vectorizer(vectorizer: str, **kwargs: dict):
    """Initialize a vectorizer by name using abstract base class discovery."""
    for cls in BaseVectorizer.__subclasses__():
        if hasattr(cls, "name") and cls.name == vectorizer:
            return cls(**kwargs)
    raise ValueError(
        f"Unknown vectorizer: {vectorizer}. Available: {[cls.name for cls in BaseVectorizer.__subclasses__() if hasattr(cls, 'name')]}"
    )
