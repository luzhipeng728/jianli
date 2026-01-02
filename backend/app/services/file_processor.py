import io
import chardet
import pdfplumber
from docx import Document
from PIL import Image
from pathlib import Path
from enum import Enum

class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"
    UNKNOWN = "unknown"

class FileProcessor:
    SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def detect_file_type(self, filename: str) -> FileType:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return FileType.PDF
        elif suffix in {".docx", ".doc"}:
            return FileType.DOCX
        elif suffix == ".txt":
            return FileType.TXT
        elif suffix in self.SUPPORTED_IMAGES:
            return FileType.IMAGE
        return FileType.UNKNOWN

    def extract_text_from_pdf(self, file_content: bytes) -> str:
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def extract_text_from_docx(self, file_content: bytes) -> str:
        doc = Document(io.BytesIO(file_content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def extract_text_from_txt(self, file_content: bytes) -> str:
        detected = chardet.detect(file_content)
        encoding = detected.get("encoding", "utf-8") or "utf-8"
        return file_content.decode(encoding)

    def process_file(self, filename: str, content: bytes) -> tuple[FileType, str]:
        file_type = self.detect_file_type(filename)

        if file_type == FileType.PDF:
            text = self.extract_text_from_pdf(content)
        elif file_type == FileType.DOCX:
            text = self.extract_text_from_docx(content)
        elif file_type == FileType.TXT:
            text = self.extract_text_from_txt(content)
        elif file_type == FileType.IMAGE:
            text = ""  # 需要OCR处理，返回空，由上层调用LLM OCR
        else:
            text = ""

        return file_type, text
