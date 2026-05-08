from django.conf import settings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = (
    'You are the official chatbot of the Academy of Arts in Egypt.\n'
    'You answer questions strictly based on the provided context only.\n'
    'You must not answer anything outside the provided context.\n'
    'If the context does not contain enough information, respond exactly with: INSUFFICIENT_DATA\n'
    'If the context addresses a different subject than what the user asked about, respond exactly with: INSUFFICIENT_DATA\n'
    'Be formal and institutional in tone.\n'
    'Never make up information. Never guess.\n'
    'When the context contains a list or multiple points, include ALL of them without omitting any.'
)


def get_llm():
    if settings.LLM_PROVIDER == 'deepseek':
        return ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url='https://api.deepseek.com/v1',
            model='deepseek-chat',
        )
    return ChatGroq(api_key=settings.GROQ_API_KEY, model='llama-3.3-70b-versatile')


def build_prompt(language: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ('system', SYSTEM_PROMPT),
        ('human', 'Context:\n{context}\n\nQuestion: {question}\n\nYou MUST respond in {language} only.'),
    ])


def build_chat_prompt(language: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ('system', SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name='history'),
        ('human', 'Context:\n{context}\n\nQuestion: {question}\n\nYou MUST respond in {language} only.'),
    ])
