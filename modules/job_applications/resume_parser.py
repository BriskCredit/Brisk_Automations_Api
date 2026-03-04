import os
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger("app.modules.job_applications.resume_parser")


class ResumeParserService:
    """
    Service for parsing and extracting text from resume files (PDF).
    Uses PyMuPDF (fitz) for PDF text extraction.
    """
    
    def __init__(self):
        """Initialize the resume parser service."""
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            import fitz  # PyMuPDF
            self.fitz_available = True
        except ImportError:
            self.fitz_available = False
            logger.warning("PyMuPDF (fitz) not installed. PDF parsing will not be available.")
    
    def extract_text_from_pdf(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text content from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, error_message)
            Returns (None, error) if extraction fails
        """
        if not self.fitz_available:
            return None, "PDF parsing not available. Install PyMuPDF: pip install pymupdf"
        
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"
        
        try:
            import fitz
            
            text_content = []
            
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    if page_text.strip():
                        text_content.append(page_text)
                    
                    logger.debug(f"Extracted text from page {page_num + 1}")
            
            if not text_content:
                return None, "No text content found in PDF (may be image-based)"
            
            full_text = "\n\n".join(text_content)
            
            # Clean up the text
            full_text = self._clean_text(full_text)
            
            logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
            return full_text, None
            
        except Exception as e:
            error_msg = f"Error extracting text from PDF: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def extract_text_from_bytes(self, pdf_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text content from PDF bytes (for in-memory processing).
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            Tuple of (extracted_text, error_message)
        """
        if not self.fitz_available:
            return None, "PDF parsing not available. Install PyMuPDF: pip install pymupdf"
        
        try:
            import fitz
            
            text_content = []
            
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    if page_text.strip():
                        text_content.append(page_text)
            
            if not text_content:
                return None, "No text content found in PDF"
            
            full_text = "\n\n".join(text_content)
            full_text = self._clean_text(full_text)
            
            return full_text, None
            
        except Exception as e:
            error_msg = f"Error extracting text from PDF bytes: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Replace multiple newlines with double newline
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove empty lines at start and end
        text = text.strip()
        
        return text
    
    def get_pdf_metadata(self, file_path: str) -> Optional[dict]:
        """
        Extract metadata from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with metadata or None if extraction fails
        """
        if not self.fitz_available:
            return None
        
        try:
            import fitz
            
            with fitz.open(file_path) as doc:
                metadata = doc.metadata
                page_count = len(doc)
            
            return {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "page_count": page_count
            }
            
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            return None
    
    def validate_pdf(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file is a valid PDF.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, "File not found"
        
        # Check file extension
        if not file_path.lower().endswith('.pdf'):
            return False, "File is not a PDF (wrong extension)"
        
        # Check magic bytes
        try:
            with open(file_path, 'rb') as f:
                header = f.read(5)
            
            if header != b'%PDF-':
                return False, "File is not a valid PDF (invalid header)"
            
            return True, None
            
        except Exception as e:
            return False, f"Error validating PDF: {str(e)}"
    
    def validate_pdf_bytes(self, pdf_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate that bytes represent a valid PDF.
        
        Args:
            pdf_bytes: File content as bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(pdf_bytes) < 5:
            return False, "File is too small to be a valid PDF"
        
        if pdf_bytes[:5] != b'%PDF-':
            return False, "File is not a valid PDF (invalid header)"
        
        return True, None
