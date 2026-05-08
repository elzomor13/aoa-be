import threading
from pathlib import Path

from django.db.models.signals import post_save
from django.dispatch import receiver
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

_CHAR_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
_MD_CHAR_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=80)
_MD_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


def _split_markdown(text: str) -> list[str]:
    """
    Split markdown by headers first so each section stays geographically coherent
    (e.g. Alexandria section never merges with Cairo section), then apply a
    secondary character splitter for sections that are still too large.
    Each sub-chunk gets the section header prepended so the LLM always knows
    which section it is reading.
    """
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_MD_HEADERS,
        strip_headers=False,
    )
    sections = md_splitter.split_text(text)
    chunks = []
    for section in sections:
        breadcrumb = list(section.metadata.values())[-1] if section.metadata else ''
        sub_chunks = _MD_CHAR_SPLITTER.split_text(section.page_content)
        for i, chunk in enumerate(sub_chunks):
            # First sub-chunk already contains the header; prepend to the rest
            chunks.append(f'{breadcrumb}\n{chunk}' if i > 0 and breadcrumb else chunk)
    return chunks


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

    ext = Path(document.document.name).suffix.lower()
    pages = extract_text_by_page(document.document)

    all_chunks = []
    page_numbers = []
    for page_num, page_text in enumerate(pages, start=1):
        split_fn = _split_markdown if ext == '.md' else _CHAR_SPLITTER.split_text
        for chunk in split_fn(page_text):
            all_chunks.append(chunk)
            page_numbers.append(page_num)

    if not all_chunks:
        return

    embeddings = embed_documents(all_chunks)
    DocumentChunk.objects.bulk_create([
        DocumentChunk(document=document, content=text, embedding=emb, page_number=pg)
        for text, emb, pg in zip(all_chunks, embeddings, page_numbers)
    ])
