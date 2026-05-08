from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from langchain_core.documents import Document

from chatbot.services.pipeline import FALLBACK_AR, FALLBACK_EN, _is_arabic, run_pipeline


class TestIsArabic(SimpleTestCase):
    def test_detects_arabic_text(self):
        self.assertTrue(_is_arabic('ما هي مواعيد التقديم؟'))

    def test_detects_english_as_non_arabic(self):
        self.assertFalse(_is_arabic('What are the admission dates?'))

    def test_empty_string_is_non_arabic(self):
        self.assertFalse(_is_arabic(''))


@override_settings(COHERE_API_KEY='key', GROQ_API_KEY='key', LLM_PROVIDER='groq')
class TestRunPipeline(SimpleTestCase):
    def _make_doc(self, content: str) -> Document:
        return Document(page_content=content, metadata={})

    @patch('chatbot.services.pipeline.DocumentChunkRetriever')
    def test_arabic_fallback_when_no_docs(self, MockRetriever):
        MockRetriever.return_value.invoke.return_value = []
        result = run_pipeline('ما هي الأقسام المتاحة؟')
        self.assertEqual(result['answer'], FALLBACK_AR)
        self.assertFalse(result['answered'])

    @patch('chatbot.services.pipeline.DocumentChunkRetriever')
    def test_english_fallback_when_no_docs(self, MockRetriever):
        MockRetriever.return_value.invoke.return_value = []
        result = run_pipeline('What departments are available?')
        self.assertEqual(result['answer'], FALLBACK_EN)
        self.assertFalse(result['answered'])

    @patch('chatbot.services.pipeline._call_llm', return_value='INSUFFICIENT_DATA')
    @patch('chatbot.services.pipeline.DocumentChunkRetriever')
    def test_fallback_on_insufficient_data(self, MockRetriever, mock_call_llm):
        MockRetriever.return_value.invoke.return_value = [self._make_doc('some context')]
        result = run_pipeline('irrelevant question')
        self.assertFalse(result['answered'])
        self.assertEqual(result['answer'], FALLBACK_EN)

    @patch('chatbot.services.pipeline._call_llm', return_value='The Academy was founded in 1959.')
    @patch('chatbot.services.pipeline.DocumentChunkRetriever')
    def test_returns_answer_when_llm_responds(self, MockRetriever, mock_call_llm):
        MockRetriever.return_value.invoke.return_value = [self._make_doc('Founded in 1959')]
        result = run_pipeline('When was the Academy founded?')
        self.assertTrue(result['answered'])
        self.assertEqual(result['answer'], 'The Academy was founded in 1959.')

    @patch('chatbot.services.pipeline._call_llm', return_value='Some answer')
    @patch('chatbot.services.pipeline.DocumentChunkRetriever')
    def test_call_llm_receives_question_and_docs(self, MockRetriever, mock_call_llm):
        doc = self._make_doc('context text')
        MockRetriever.return_value.invoke.return_value = [doc]
        run_pipeline('test question')
        mock_call_llm.assert_called_once_with('test question', [doc])
