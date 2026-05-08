from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from chatbot.services.generator import SYSTEM_PROMPT, build_prompt, get_llm


@override_settings(
    LLM_PROVIDER='groq',
    GROQ_API_KEY='test-groq-key',
    DEEPSEEK_API_KEY='test-deepseek-key',
)
class TestGetLlm(SimpleTestCase):
    @patch('chatbot.services.generator.ChatGroq')
    def test_returns_groq_when_provider_is_groq(self, MockGroq):
        get_llm()
        MockGroq.assert_called_once_with(
            api_key='test-groq-key',
            model='llama-3.3-70b-versatile',
        )

    @override_settings(LLM_PROVIDER='deepseek')
    @patch('chatbot.services.generator.ChatOpenAI')
    def test_returns_openai_when_provider_is_deepseek(self, MockOpenAI):
        get_llm()
        MockOpenAI.assert_called_once_with(
            api_key='test-deepseek-key',
            base_url='https://api.deepseek.com/v1',
            model='deepseek-chat',
        )


class TestBuildPrompt(SimpleTestCase):
    def test_prompt_contains_system_message(self):
        prompt = build_prompt()
        messages = prompt.messages
        system_msg = messages[0]
        self.assertIn('INSUFFICIENT_DATA', system_msg.prompt.template)
        self.assertIn('Academy of Arts', system_msg.prompt.template)

    def test_prompt_has_context_and_question_variables(self):
        prompt = build_prompt()
        self.assertIn('context', prompt.input_variables)
        self.assertIn('question', prompt.input_variables)

    def test_system_prompt_constant_matches_expected_content(self):
        self.assertIn('Academy of Arts in Egypt', SYSTEM_PROMPT)
        self.assertIn('INSUFFICIENT_DATA', SYSTEM_PROMPT)
        self.assertIn('Never make up information', SYSTEM_PROMPT)
