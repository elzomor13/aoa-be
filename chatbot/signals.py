import threading

from django.db.models.signals import post_save
from django.dispatch import receiver
from langchain_text_splitters import RecursiveCharacterTextSplitter


@receiver(post_save, sender='base_documents.BaseDocument')
def index_document(sender, instance, **kwargs):
    from chatbot.models import DocumentChunk

    if not instance.is_active:
        DocumentChunk.objects.filter(document=instance).delete()
        return

    thread = threading.Thread(target=_do_index, args=(instance,), daemon=True)
    thread.start()


def _do_index(document):
    from chatbot.models import DocumentChunk
    from chatbot.services.embedder import embed_documents
    from chatbot.services.parser import extract_text_by_page

    DocumentChunk.objects.filter(document=document).delete()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    pages = extract_text_by_page(document.document)

    all_chunks = []
    page_numbers = []
    for page_num, page_text in enumerate(pages, start=1):
        for chunk in splitter.split_text(page_text):
            all_chunks.append(chunk)
            page_numbers.append(page_num)

    if not all_chunks:
        return

    embeddings = embed_documents(all_chunks)
    DocumentChunk.objects.bulk_create([
        DocumentChunk(document=document, content=text, embedding=emb, page_number=pg)
        for text, emb, pg in zip(all_chunks, embeddings, page_numbers)
    ])
