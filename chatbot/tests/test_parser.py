import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from chatbot.services.parser import extract_text_by_page


def _make_field(data: bytes, filename: str) -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=ctx)
    ctx.__exit__ = MagicMock(return_value=False)
    ctx.read.return_value = data
    field = MagicMock()
    field.open.return_value = ctx
    field.name = filename
    return field


class TestPdfParser(SimpleTestCase):
    def _make_page(self, text: str) -> MagicMock:
        page = MagicMock()
        page.get_text.return_value = text
        return page

    @patch('chatbot.services.parser.fitz.open')
    def test_returns_non_empty_pages(self, mock_fitz_open):
        pages = [
            self._make_page('First page content'),
            self._make_page('   '),
            self._make_page('Third page content'),
        ]
        mock_pdf = MagicMock()
        mock_pdf.__iter__ = MagicMock(return_value=iter(pages))
        mock_fitz_open.return_value = mock_pdf

        result = extract_text_by_page(_make_field(b'fake-pdf', 'doc.pdf'))

        self.assertEqual(result, ['First page content', 'Third page content'])

    @patch('chatbot.services.parser.fitz.open')
    def test_empty_pdf_returns_empty_list(self, mock_fitz_open):
        mock_pdf = MagicMock()
        mock_pdf.__iter__ = MagicMock(return_value=iter([]))
        mock_fitz_open.return_value = mock_pdf

        result = extract_text_by_page(_make_field(b'', 'doc.pdf'))

        self.assertEqual(result, [])

    @patch('chatbot.services.parser.fitz.open')
    def test_passes_stream_to_fitz(self, mock_fitz_open):
        mock_pdf = MagicMock()
        mock_pdf.__iter__ = MagicMock(return_value=iter([]))
        mock_fitz_open.return_value = mock_pdf

        extract_text_by_page(_make_field(b'pdf-bytes', 'doc.pdf'))

        mock_fitz_open.assert_called_once_with(stream=b'pdf-bytes', filetype='pdf')


class TestDocxParser(SimpleTestCase):
    @patch('chatbot.services.parser.docx.Document')
    def test_returns_paragraphs_as_single_page(self, mock_document):
        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            MagicMock(text='First paragraph'),
            MagicMock(text=''),
            MagicMock(text='Second paragraph'),
        ]
        mock_document.return_value = mock_doc

        result = extract_text_by_page(_make_field(b'fake-docx', 'doc.docx'))

        self.assertEqual(result, ['First paragraph\nSecond paragraph'])

    @patch('chatbot.services.parser.docx.Document')
    def test_empty_docx_returns_empty_list(self, mock_document):
        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_document.return_value = mock_doc

        result = extract_text_by_page(_make_field(b'', 'doc.docx'))

        self.assertEqual(result, [])


class TestMarkdownParser(SimpleTestCase):
    def test_returns_content_as_single_page(self):
        content = '# Title\n\nSome content here.'
        result = extract_text_by_page(_make_field(content.encode(), 'doc.md'))
        self.assertEqual(result, [content])

    def test_empty_file_returns_empty_list(self):
        result = extract_text_by_page(_make_field(b'   ', 'doc.md'))
        self.assertEqual(result, [])


class TestJsonParser(SimpleTestCase):
    def test_flattens_dict_to_text(self):
        data = json.dumps({'name': 'Academy', 'city': 'Cairo'}).encode()
        result = extract_text_by_page(_make_field(data, 'doc.json'))
        self.assertEqual(len(result), 1)
        self.assertIn('name: Academy', result[0])
        self.assertIn('city: Cairo', result[0])

    def test_flattens_nested_structure(self):
        data = json.dumps({'goals': ['goal one', 'goal two']}).encode()
        result = extract_text_by_page(_make_field(data, 'doc.json'))
        self.assertIn('goal one', result[0])
        self.assertIn('goal two', result[0])

    def test_empty_object_returns_empty_list(self):
        data = json.dumps({}).encode()
        result = extract_text_by_page(_make_field(data, 'doc.json'))
        self.assertEqual(result, [])


class TestUnsupportedFormat(SimpleTestCase):
    def test_raises_for_unknown_extension(self):
        with self.assertRaises(ValueError):
            extract_text_by_page(_make_field(b'data', 'doc.txt'))
