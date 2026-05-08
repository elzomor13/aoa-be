import uuid

from django.db import models
from pgvector.django import VectorField


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)

    def __str__(self):
        return str(self.id)


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        'base_documents.BaseDocument',
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    content = models.TextField()
    embedding = VectorField(dimensions=1024)
    page_number = models.IntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Chunk {self.id} — {self.document.title} p.{self.page_number}'


class ChatLog(models.Model):
    session = models.ForeignKey(
        ChatSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='logs',
    )
    question = models.TextField()
    answer = models.TextField()
    was_answered = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)

    def __str__(self):
        return f'ChatLog {self.id} — answered={self.was_answered}'
