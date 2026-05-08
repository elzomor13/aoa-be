from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from langchain_core.documents import Document

from chatbot.services.retriever import DocumentChunkRetriever


class TestDocumentChunkRetriever(SimpleTestCase):
    def _make_chunk(self, chunk_id: int, content: str, page: int) -> MagicMock:
        chunk = MagicMock()
        chunk.id = chunk_id
        chunk.content = content
        chunk.page_number = page
        return chunk

    @patch('chatbot.services.retriever._embed_query')
    @patch('chatbot.services.retriever.DocumentChunk')
    def test_returns_langchain_documents(self, MockChunk, mock_embed):
        mock_embed.return_value = [0.1] * 1024
        chunk = self._make_chunk(1, 'Academy founded in 1959', 3)

        mock_qs = MagicMock()
        mock_qs.annotate.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__getitem__ = MagicMock(return_value=[chunk])
        MockChunk.objects = mock_qs

        retriever = DocumentChunkRetriever()
        docs = retriever.invoke('When was the Academy founded?')

        self.assertEqual(len(docs), 1)
        self.assertIsInstance(docs[0], Document)
        self.assertEqual(docs[0].page_content, 'Academy founded in 1959')
        self.assertEqual(docs[0].metadata['page_number'], 3)
        self.assertEqual(docs[0].metadata['chunk_id'], 1)

    @patch('chatbot.services.retriever._embed_query')
    @patch('chatbot.services.retriever.DocumentChunk')
    def test_returns_empty_list_when_no_chunks(self, MockChunk, mock_embed):
        mock_embed.return_value = [0.0] * 1024

        mock_qs = MagicMock()
        mock_qs.annotate.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__getitem__ = MagicMock(return_value=[])
        MockChunk.objects = mock_qs

        retriever = DocumentChunkRetriever()
        docs = retriever.invoke('unrelated question')

        self.assertEqual(docs, [])

    @patch('chatbot.services.retriever._embed_query')
    @patch('chatbot.services.retriever.DocumentChunk')
    def test_filters_by_cosine_distance_threshold(self, MockChunk, mock_embed):
        mock_embed.return_value = [0.1] * 1024

        mock_qs = MagicMock()
        mock_qs.annotate.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        mock_qs.__getitem__ = MagicMock(return_value=[])
        MockChunk.objects = mock_qs

        retriever = DocumentChunkRetriever(threshold=0.45)
        retriever.invoke('test query')

        filter_call_kwargs = mock_qs.filter.call_args
        self.assertIn('distance__lte', filter_call_kwargs.kwargs)
        self.assertAlmostEqual(filter_call_kwargs.kwargs['distance__lte'], 0.55)
