"""
OCR Processor Module
Handles OCR processing and saves results as markdown files
"""
import os
import logging
import base64
from typing import Optional
from dataclasses import dataclass
import threading
from mistralai import Mistral


@dataclass
class OCRResult:
    """Result from OCR processing"""
    file_path: str
    markdown_content: str
    page_count: int
    success: bool
    error_message: Optional[str] = None


class OCRProcessor:
    """Handles OCR processing using Mistral OCR"""
    
    def __init__(self, api_key: str, model_name: str, output_dir: str, logger: logging.Logger):
        """
        Initialize OCR Processor
        
        Args:
            api_key: Mistral API key
            model_name: Mistral OCR model name
            output_dir: Directory to save OCR markdown results
            logger: Logger instance
        """
        if not api_key:
            raise ValueError("Mistral API key is required.")
        
        self.client = Mistral(api_key=api_key)
        self.model_name = model_name
        self.output_dir = output_dir
        self.logger = logger
        
        # Create output directory for OCR results
        os.makedirs(output_dir, exist_ok=True)
        
        self.logger.info(f"OCRProcessor initialized with model '{self.model_name}'.")
        self.logger.info(f"OCR results will be saved to: {self.output_dir}")
    
    def process_document(self, file_path: str, save_markdown: bool = True) -> OCRResult:
        """
        Process a document with OCR and optionally save the markdown result
        
        Args:
            file_path: Path to the document to process
            save_markdown: Whether to save OCR results as markdown file
            
        Returns:
            OCRResult object containing the results
        """
        thread_name = threading.current_thread().name
        filename = os.path.basename(file_path)
        
        self.logger.info(f"[{thread_name}] Starting OCR for: {filename}")
        
        try:
            # Read file and encode to base64
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            
            file_data_b64 = base64.b64encode(file_bytes).decode("utf-8")
            
            # Determine media type
            ext = os.path.splitext(file_path)[1].lower()
            media_type_map = {
                ".pdf": "application/pdf",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg"
            }
            media_type = media_type_map.get(ext, "application/octet-stream")
            
            # Perform OCR
            ocr_response = self.client.ocr.process(
                model=self.model_name,
                document={
                    "type": "document_url",
                    "document_url": f"data:{media_type};base64,{file_data_b64}"
                }
            )
            
            if not ocr_response.pages:
                self.logger.warning(f"[{thread_name}] OCR returned no pages for {filename}")
                return OCRResult(
                    file_path=file_path,
                    markdown_content="",
                    page_count=0,
                    success=False,
                    error_message="No pages returned from OCR"
                )
            
            # Combine all pages into markdown
            markdown_content = "\n\n---\n\n".join([page.markdown for page in ocr_response.pages])
            page_count = len(ocr_response.pages)
            
            # Save markdown file if requested
            if save_markdown:
                base_name = os.path.splitext(filename)[0]
                markdown_path = os.path.join(self.output_dir, f"{base_name}_ocr.md")
                
                with open(markdown_path, "w", encoding="utf-8") as f:
                    f.write(f"# OCR Result for: {filename}\n\n")
                    f.write(f"**Total Pages:** {page_count}\n\n")
                    f.write(f"**Source File:** {file_path}\n\n")
                    f.write("---\n\n")
                    f.write(markdown_content)
                
                self.logger.info(f"[{thread_name}] OCR result saved to: {markdown_path}")
            
            self.logger.info(f"[{thread_name}] OCR Complete for {filename} ({page_count} pages)")
            
            return OCRResult(
                file_path=file_path,
                markdown_content=markdown_content,
                page_count=page_count,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"[{thread_name}] OCR failed for {filename}: {e}", exc_info=True)
            return OCRResult(
                file_path=file_path,
                markdown_content="",
                page_count=0,
                success=False,
                error_message=str(e)
            )
    
    def get_ocr_output_path(self, source_file: str) -> str:
        """Get the expected output path for OCR markdown file"""
        base_name = os.path.splitext(os.path.basename(source_file))[0]
        return os.path.join(self.output_dir, f"{base_name}_ocr.md")
