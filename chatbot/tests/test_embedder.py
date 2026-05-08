from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings


def _make_embedding_response(vectors: list[list[float]]) -> MagicMock:
    response = MagicMock()
    response.data = [MagicMock(embedding=v) for v in vectors]
    return response


@override_settings(TOGETHER_API_KEY='test-key')
class TestEmbedder(SimpleTestCase):
    @patch('chatbot.services.embedder.OpenAI')
    def test_embed_documents_returns_vectors(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = _make_embedding_response(
            [[0.1] * 1024, [0.2] * 1024]
        )
        MockOpenAI.return_value = mock_client

        from chatbot.services.embedder import embed_documents
        result = embed_documents(['text one', 'text two'])

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 1024)
        mock_client.embeddings.create.assert_called_once_with(
            model='intfloat/multilingual-e5-large-instruct',
            input=['passage: text one', 'passage: text two'],
        )

    @patch('chatbot.services.embedder.OpenAI')
    def test_embed_query_returns_single_vector(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = _make_embedding_response([[0.5] * 1024])
        MockOpenAI.return_value = mock_client

        from chatbot.services.embedder import embed_query
        result = embed_query('what is the deadline?')

        self.assertEqual(len(result), 1024)

    @patch('chatbot.services.embedder.OpenAI')
    def test_embed_query_prepends_query_prefix(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = _make_embedding_response([[0.0] * 1024])
        MockOpenAI.return_value = mock_client

        from chatbot.services.embedder import embed_query
        embed_query('test')

        mock_client.embeddings.create.assert_called_once_with(
            model='intfloat/multilingual-e5-large-instruct',
            input='query: test',
        )

    @patch('chatbot.services.embedder.OpenAI')
    def test_client_instantiated_with_correct_params(self, MockOpenAI):
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = _make_embedding_response([[0.0] * 1024])
        MockOpenAI.return_value = mock_client

        from chatbot.services.embedder import embed_query
        embed_query('test')

        MockOpenAI.assert_called_once_with(
            api_key='test-key',
            base_url='https://api.together.xyz/v1',
        )
