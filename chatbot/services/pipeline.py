import json

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from chatbot.services.generator import build_chat_prompt, build_prompt, get_llm
from chatbot.services.retriever import DocumentChunkRetriever

_HISTORY_LIMIT = 10  # number of past exchanges to include

FALLBACK_AR = (
    'عذراً، هذه المعلومة غير متوفرة حالياً. '
    'يُرجى التواصل مع الأكاديمية مباشرةً عبر البريد الإلكتروني.'
)
FALLBACK_EN = (
    'Sorry, this information is not currently available. '
    'Please contact the Academy directly via email.'
)


def _is_arabic(text: str) -> bool:
    return any('؀' <= c <= 'ۿ' for c in text)


def _format_docs(docs) -> str:
    return '\n\n'.join(doc.page_content for doc in docs)


def _build_chain(docs: list, language: str):
    return (
        {
            'context': RunnableLambda(lambda _: _format_docs(docs)),
            'question': RunnablePassthrough(),
            'language': RunnableLambda(lambda _: language),
        }
        | build_prompt(language)
        | get_llm()
        | StrOutputParser()
    )


def _call_llm(question: str, docs: list, language: str) -> str:
    return _build_chain(docs, language).invoke(question)


def run_pipeline(question: str) -> dict:
    retriever = DocumentChunkRetriever()
    docs = retriever.invoke(question)

    arabic = _is_arabic(question)
    language = 'Arabic' if arabic else 'English'
    fallback = FALLBACK_AR if arabic else FALLBACK_EN

    if not docs:
        return {'answer': fallback, 'answered': False}

    answer = _call_llm(question, docs, language)

    if answer.strip() == 'INSUFFICIENT_DATA':
        return {'answer': fallback, 'answered': False}

    return {'answer': answer, 'answered': True}


def _build_history(session_id) -> list:
    from chatbot.models import ChatLog
    logs = ChatLog.objects.filter(session_id=session_id).order_by('created_at')[: _HISTORY_LIMIT * 2]
    history = []
    for log in logs:
        history.append(HumanMessage(content=log.question))
        history.append(AIMessage(content=log.answer))
    return history


def _build_chat_chain(docs: list, language: str, history: list):
    return (
        {
            'context': RunnableLambda(lambda _: _format_docs(docs)),
            'question': RunnablePassthrough(),
            'language': RunnableLambda(lambda _: language),
            'history': RunnableLambda(lambda _: history),
        }
        | build_chat_prompt(language)
        | get_llm()
        | StrOutputParser()
    )


def run_chat_pipeline(question: str, session_id) -> dict:
    retriever = DocumentChunkRetriever()
    docs = retriever.invoke(question)

    arabic = _is_arabic(question)
    language = 'Arabic' if arabic else 'English'
    fallback = FALLBACK_AR if arabic else FALLBACK_EN

    if not docs:
        return {'answer': fallback, 'answered': False}

    history = _build_history(session_id)
    answer = _build_chat_chain(docs, language, history).invoke(question)

    if answer.strip() == 'INSUFFICIENT_DATA':
        return {'answer': fallback, 'answered': False}

    return {'answer': answer, 'answered': True}


def stream_chat_pipeline(question: str, session_id):
    retriever = DocumentChunkRetriever()
    docs = retriever.invoke(question)

    arabic = _is_arabic(question)
    language = 'Arabic' if arabic else 'English'
    fallback = FALLBACK_AR if arabic else FALLBACK_EN

    if not docs:
        yield f'data: {json.dumps({"done": True, "answered": False, "fallback": fallback})}\n\n'
        return

    history = _build_history(session_id)
    full_answer = ''
    for chunk in _build_chat_chain(docs, language, history).stream(question):
        full_answer += chunk
        yield f'data: {json.dumps({"token": chunk})}\n\n'

    if full_answer.strip() == 'INSUFFICIENT_DATA':
        yield f'data: {json.dumps({"done": True, "answered": False, "fallback": fallback})}\n\n'
    else:
        yield f'data: {json.dumps({"done": True, "answered": True, "fallback": None})}\n\n'


def stream_pipeline(question: str):
    """
    Yields SSE-ready strings.
    Token events : data: {"token": "..."}\n\n
    Final event  : data: {"done": true, "answered": bool, "fallback": str|null}\n\n
    """
    retriever = DocumentChunkRetriever()
    docs = retriever.invoke(question)

    arabic = _is_arabic(question)
    language = 'Arabic' if arabic else 'English'
    fallback = FALLBACK_AR if arabic else FALLBACK_EN

    if not docs:
        yield f'data: {json.dumps({"done": True, "answered": False, "fallback": fallback})}\n\n'
        return

    full_answer = ''
    for chunk in _build_chain(docs, language).stream(question):
        full_answer += chunk
        yield f'data: {json.dumps({"token": chunk})}\n\n'

    if full_answer.strip() == 'INSUFFICIENT_DATA':
        yield f'data: {json.dumps({"done": True, "answered": False, "fallback": fallback})}\n\n'
    else:
        yield f'data: {json.dumps({"done": True, "answered": True, "fallback": None})}\n\n'
