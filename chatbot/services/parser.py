import json
from io import BytesIO
from pathlib import Path

import docx
import fitz


def _extract_pdf(data: bytes) -> list[str]:
    pdf = fitz.open(stream=data, filetype='pdf')
    pages = [page.get_text('text').strip() for page in pdf]
    pdf.close()
    return [p for p in pages if p]


def _extract_docx(data: bytes) -> list[str]:
    doc = docx.Document(BytesIO(data))
    text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    return [text] if text else []


def _extract_md(data: bytes) -> list[str]:
    text = data.decode('utf-8').strip()
    return [text] if text else []


def _flatten_json(obj) -> str:
    if isinstance(obj, dict):
        return '\n'.join(f'{k}: {_flatten_json(v)}' for k, v in obj.items())
    if isinstance(obj, list):
        return '\n'.join(_flatten_json(item) for item in obj)
    return str(obj)


def _extract_json(data: bytes) -> list[str]:
    text = _flatten_json(json.loads(data.decode('utf-8')))
    return [text] if text else []


_EXTRACTORS = {
    '.pdf': _extract_pdf,
    '.docx': _extract_docx,
    '.md': _extract_md,
    '.json': _extract_json,
}


def extract_text_by_page(document_field) -> list[str]:
    ext = Path(document_field.name).suffix.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise ValueError(f'Unsupported file type: {ext}')
    with document_field.open('rb') as f:
        data = f.read()
    return extractor(data)
