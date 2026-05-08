import django.db.models.deletion
import pgvector.django
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('base_documents', '0001_initial'),
        ('chatbot', '0001_pgvector_extension'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('answer', models.TextField()),
                ('was_answered', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DocumentChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('embedding', pgvector.django.VectorField(dimensions=1024)),
                ('page_number', models.IntegerField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chunks',
                    to='base_documents.basedocument',
                )),
            ],
        ),
    ]
