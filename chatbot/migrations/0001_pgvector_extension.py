from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('base_documents', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS vector;',
            reverse_sql='DROP EXTENSION IF EXISTS vector;',
        ),
    ]
