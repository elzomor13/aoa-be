from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from chatbot.models import ChatLog


@override_settings(
    COHERE_API_KEY='key',
    GROQ_API_KEY='key',
    LLM_PROVIDER='groq',
)
class TestAskView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('chatbot-ask')

    def test_returns_400_when_question_missing(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_returns_400_when_question_is_blank(self):
        response = self.client.post(self.url, {'question': '   '}, format='json')
        self.assertEqual(response.status_code, 400)

    @patch('chatbot.views.run_pipeline')
    def test_returns_200_with_answer(self, mock_pipeline):
        mock_pipeline.return_value = {
            'answer': 'The Academy was founded in 1959.',
            'answered': True,
        }
        response = self.client.post(self.url, {'question': 'When was it founded?'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['answer'], 'The Academy was founded in 1959.')
        self.assertTrue(response.data['answered'])

    @patch('chatbot.views.run_pipeline')
    def test_creates_chat_log_on_valid_request(self, mock_pipeline):
        mock_pipeline.return_value = {'answer': 'Some answer', 'answered': True}
        self.client.post(self.url, {'question': 'Test question?'}, format='json')
        self.assertEqual(ChatLog.objects.count(), 1)
        log = ChatLog.objects.first()
        self.assertEqual(log.question, 'Test question?')
        self.assertEqual(log.answer, 'Some answer')
        self.assertTrue(log.was_answered)

    @patch('chatbot.views._check_rate_limit', return_value=False)
    @patch('chatbot.views.run_pipeline')
    def test_returns_429_when_rate_limit_exceeded(self, mock_pipeline, mock_rate):
        response = self.client.post(self.url, {'question': 'any question'}, format='json')
        self.assertEqual(response.status_code, 429)
        mock_pipeline.assert_not_called()

    @patch('chatbot.views.run_pipeline')
    def test_chat_log_stores_ip_address(self, mock_pipeline):
        mock_pipeline.return_value = {'answer': 'Answer', 'answered': True}
        self.client.post(
            self.url,
            {'question': 'Test?'},
            format='json',
            REMOTE_ADDR='192.168.1.1',
        )
        log = ChatLog.objects.first()
        self.assertEqual(log.ip_address, '192.168.1.1')

    @patch('chatbot.views.run_pipeline')
    def test_unanswered_chat_log_records_was_answered_false(self, mock_pipeline):
        mock_pipeline.return_value = {'answer': 'Sorry, not available.', 'answered': False}
        self.client.post(self.url, {'question': 'Unknown topic'}, format='json')
        log = ChatLog.objects.first()
        self.assertFalse(log.was_answered)
