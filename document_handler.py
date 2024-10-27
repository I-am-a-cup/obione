import logging
from docx import Document

def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        return '\n'.join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        logging.error(f"Ошибка при извлечении текста: {e}")
        return ""
