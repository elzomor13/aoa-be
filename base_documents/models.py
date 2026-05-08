from django.db import models


class BaseDocument(models.Model):
    title = models.CharField(max_length=100)
    document = models.FileField(upload_to='documents/')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title