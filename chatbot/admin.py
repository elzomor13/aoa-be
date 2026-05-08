from django.contrib import admin

from chatbot.models import ChatLog, ChatSession, DocumentChunk


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('document', 'page_number', 'content_preview', 'created_at')
    readonly_fields = ('document', 'content', 'embedding', 'page_number', 'created_at')

    def content_preview(self, obj):
        return obj.content[:100]
    content_preview.short_description = 'Content Preview'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'ip_address', 'created_at')
    readonly_fields = ('id', 'ip_address', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer_preview', 'was_answered', 'ip_address', 'created_at')
    list_filter = ('was_answered',)
    readonly_fields = ('question', 'answer', 'was_answered', 'ip_address', 'created_at')

    def answer_preview(self, obj):
        return obj.answer[:100]
    answer_preview.short_description = 'Answer Preview'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
