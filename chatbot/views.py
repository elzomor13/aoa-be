import json
import logging

from django.core.cache import cache
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger('chatbot')

from django.conf import settings

from chatbot.models import ChatLog, ChatSession
from chatbot.services.pipeline import run_chat_pipeline, run_pipeline, stream_chat_pipeline, stream_pipeline


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


def _check_rate_limit(ip: str) -> bool:
    key = f'chatbot_rate_{ip}'
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=settings.IP_RATE_WINDOW)
        count = 1
    if count > settings.IP_RATE_LIMIT:
        logger.warning('ip_rate_limit_exceeded ip=%s count=%d', ip, count)
        return False
    return True


def _check_session_limit(session: ChatSession) -> bool:
    return ChatLog.objects.filter(session=session).count() < settings.CHAT_SESSION_LIMIT


def _get_or_create_session(session_id: str | None, ip: str) -> ChatSession:
    if session_id:
        try:
            return ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            pass
    return ChatSession.objects.create(ip_address=ip)


class AskView(APIView):
    def post(self, request):
        question = request.data.get('question', '').strip()
        if not question:
            return Response({'error': 'question is required'}, status=status.HTTP_400_BAD_REQUEST)

        ip = _get_client_ip(request)
        if not _check_rate_limit(ip):
            return Response({'error': 'Rate limit exceeded'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        result = run_pipeline(question)
        ChatLog.objects.create(
            question=question,
            answer=result['answer'],
            was_answered=result['answered'],
            ip_address=ip,
        )
        logger.info('ask ip=%s answered=%s', ip, result['answered'])
        return Response({'answer': result['answer'], 'answered': result['answered']})


class AskStreamView(APIView):
    def post(self, request):
        question = request.data.get('question', '').strip()
        if not question:
            return Response({'error': 'question is required'}, status=status.HTTP_400_BAD_REQUEST)

        ip = _get_client_ip(request)
        if not _check_rate_limit(ip):
            return Response({'error': 'Rate limit exceeded'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        return StreamingHttpResponse(
            self._event_stream(question, ip),
            content_type='text/event-stream',
        )

    def _event_stream(self, question: str, ip: str):
        full_answer = ''
        answered = False

        for event in stream_pipeline(question):
            yield event
            payload = json.loads(event.removeprefix('data: '))
            if 'token' in payload:
                full_answer += payload['token']
            elif payload.get('done'):
                answered = payload['answered']
                if not answered:
                    full_answer = payload['fallback']

        ChatLog.objects.create(
            question=question,
            answer=full_answer,
            was_answered=answered,
            ip_address=ip,
        )
        logger.info('ask_stream ip=%s answered=%s', ip, answered)


class ChatView(APIView):
    def post(self, request):
        question = request.data.get('question', '').strip()
        if not question:
            return Response({'error': 'question is required'}, status=status.HTTP_400_BAD_REQUEST)

        ip = _get_client_ip(request)
        if not _check_rate_limit(ip):
            return Response({'error': 'Rate limit exceeded'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        session = _get_or_create_session(request.data.get('session_id'), ip)

        if not _check_session_limit(session):
            logger.warning('session_limit_exceeded ip=%s session=%s', ip, session.id)
            return Response(
                {'error': 'Session message limit reached', 'session_id': str(session.id)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        result = run_chat_pipeline(question, session.id)
        ChatLog.objects.create(
            session=session,
            question=question,
            answer=result['answer'],
            was_answered=result['answered'],
            ip_address=ip,
        )
        logger.info('chat ip=%s session=%s answered=%s', ip, session.id, result['answered'])
        return Response({
            'session_id': str(session.id),
            'answer': result['answer'],
            'answered': result['answered'],
        })


class ChatStreamView(APIView):
    def post(self, request):
        question = request.data.get('question', '').strip()
        if not question:
            return Response({'error': 'question is required'}, status=status.HTTP_400_BAD_REQUEST)

        ip = _get_client_ip(request)
        if not _check_rate_limit(ip):
            return Response({'error': 'Rate limit exceeded'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        session = _get_or_create_session(request.data.get('session_id'), ip)

        if not _check_session_limit(session):
            logger.warning('session_limit_exceeded ip=%s session=%s', ip, session.id)
            return Response(
                {'error': 'Session message limit reached', 'session_id': str(session.id)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        response = StreamingHttpResponse(
            self._event_stream(question, ip, session),
            content_type='text/event-stream',
        )
        response['X-Session-Id'] = str(session.id)
        return response

    def _event_stream(self, question: str, ip: str, session: ChatSession):
        full_answer = ''
        answered = False

        yield f'data: {json.dumps({"session_id": str(session.id)})}\n\n'

        for event in stream_chat_pipeline(question, session.id):
            yield event
            payload = json.loads(event.removeprefix('data: '))
            if 'token' in payload:
                full_answer += payload['token']
            elif payload.get('done'):
                answered = payload['answered']
                if not answered:
                    full_answer = payload['fallback']

        ChatLog.objects.create(
            session=session,
            question=question,
            answer=full_answer,
            was_answered=answered,
            ip_address=ip,
        )
        logger.info('chat_stream ip=%s session=%s answered=%s', ip, session.id, answered)
