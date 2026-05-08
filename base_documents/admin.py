from django.contrib import admin

from base_documents.models import BaseDocument


@admin.register(BaseDocument)
class DocumentAdmin(admin.ModelAdmin):
    pass
