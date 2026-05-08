from django.conf import settings
from openai import OpenAI

_MODEL = "intfloat/multilingual-e5-large-instruct"
_BASE_URL = "https://api.together.xyz/v1"


def _get_client() -> OpenAI:
    return OpenAI(api_key=settings.TOGETHER_API_KEY, base_url=_BASE_URL)


def embed_documents(texts: list[str]) -> list[list[float]]:
    prefixed = [f"passage: {t}" for t in texts]
    response = _get_client().embeddings.create(model=_MODEL, input=prefixed)
    return [item.embedding for item in response.data]


def embed_query(text: str) -> list[float]:
    response = _get_client().embeddings.create(model=_MODEL, input=f"query: {text}")
    return response.data[0].embedding
