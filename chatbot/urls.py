from django.urls import path

from chatbot.views import AskStreamView, AskView, ChatStreamView, ChatView

urlpatterns = [
    path('ask', AskView.as_view(), name='chatbot-ask'),
    path('ask/stream', AskStreamView.as_view(), name='chatbot-ask-stream'),
    path('chat', ChatView.as_view(), name='chatbot-chat'),
    path('chat/stream', ChatStreamView.as_view(), name='chatbot-chat-stream'),
]
