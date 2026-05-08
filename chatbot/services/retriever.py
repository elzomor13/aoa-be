from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pgvector.django import CosineDistance

from chatbot.models import DocumentChunk
from chatbot.services.embedder import embed_query as _embed_query


class DocumentChunkRetriever(BaseRetriever):
    top_k: int = 10
    threshold: float = 0.45

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        query_embedding = _embed_query(query)
        chunks = (
            DocumentChunk.objects
            .annotate(distance=CosineDistance('embedding', query_embedding))
            .filter(distance__lte=(1.0 - self.threshold))
            .order_by('distance')[:self.top_k]
        )
        return [
            Document(
                page_content=chunk.content,
                metadata={'page_number': chunk.page_number, 'chunk_id': chunk.id},
            )
            for chunk in chunks
        ]
