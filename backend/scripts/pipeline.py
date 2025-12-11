"""
Document Processing Pipeline
Orchestrates OCR, parsing, and structured extraction
"""
import os
import logging
import time
from typing import List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

from ocr_processor import OCRProcessor, OCRResult
from markdown_parser import MarkdownParser, MarkdownSection
from gemini_parser import GeminiParser, ParseResult


# Load environment variables
load_dotenv()


@dataclass
class PipelineConfig:
    """Configuration for the document processing pipeline"""
    
    # API Keys
    mistral_api_key: str
    google_api_key: str
    
    # Model Names
    mistral_ocr_model: str = "mistral-ocr-latest"
    gemini_parser_model: str = "gemini-flash-latest"
    
    # Directory Paths
    input_dir: str = "/Users/chiru/Projects/Nexus/scripts/input_documents"
    ocr_output_dir: str = "/Users/chiru/Projects/Nexus/scripts/ocr_results"
    sections_dir: str = "/Users/chiru/Projects/Nexus/scripts/markdown_sections"
    structured_output_dir: str = "/Users/chiru/Projects/Nexus/scripts/output_structured"
    
    # Processing Options
    max_workers: int = 5
    save_ocr_markdown: bool = True
    split_by_item_code: bool = True
    max_lines_per_section: int = 500
    
    # Logging
    log_file: str = "pipeline.log"
    log_level: int = logging.INFO
    
    @classmethod
    def from_env(cls) -> 'PipelineConfig':
        """Create configuration from environment variables"""
        mistral_key = os.getenv("MISTRAL_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        
        if not mistral_key or not google_key:
            raise ValueError("MISTRAL_API_KEY and GOOGLE_API_KEY must be set in environment")
        
        return cls(
            mistral_api_key=mistral_key,
            google_api_key=google_key
        )


class DocumentPipeline:
    """Main pipeline for processing documents from OCR to structured output"""
    
    def __init__(self, config: PipelineConfig):
        """
        Initialize the document processing pipeline
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        
        # Setup logging
        self._setup_logging()
        
        # Initialize processors
        self.ocr_processor = OCRProcessor(
            api_key=config.mistral_api_key,
            model_name=config.mistral_ocr_model,
            output_dir=config.ocr_output_dir,
            logger=logging.getLogger("OCRProcessor")
        )
        
        self.markdown_parser = MarkdownParser(
            logger=logging.getLogger("MarkdownParser")
        )
        
        # Custom generation config for large documents
        gemini_gen_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 16384,  # Increased for large item codes with many components
        }
        
        self.gemini_parser = GeminiParser(
            api_key=config.google_api_key,
            model_name=config.gemini_parser_model,
            output_dir=config.structured_output_dir,
            logger=logging.getLogger("GeminiParser"),
            generation_config=gemini_gen_config
        )
        
        self.logger = logging.getLogger("Pipeline")
        self.logger.info("Document Pipeline initialized successfully")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=self.config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.log_file, mode='w'),
                logging.StreamHandler()
            ]
        )
    
    def find_documents(self, extensions: List[str] = ['.pdf', '.png', '.jpg', '.jpeg']) -> List[str]:
        """
        Find all documents in input directory
        
        Args:
            extensions: List of file extensions to include
            
        Returns:
            List of file paths
        """
        documents = []
        
        if not os.path.exists(self.config.input_dir):
            self.logger.error(f"Input directory does not exist: {self.config.input_dir}")
            return documents
        
        for filename in os.listdir(self.config.input_dir):
            if any(filename.lower().endswith(ext) for ext in extensions):
                filepath = os.path.join(self.config.input_dir, filename)
                documents.append(filepath)
        
        self.logger.info(f"Found {len(documents)} documents to process")
        return documents
    
    def process_single_document(
        self, 
        file_path: str,
        skip_ocr: bool = False
    ) -> Tuple[bool, str]:
        """
        Process a single document through the entire pipeline
        
        Args:
            file_path: Path to the document
            skip_ocr: If True, look for existing OCR result
            
        Returns:
            Tuple of (success, message)
        """
        filename = os.path.basename(file_path)
        self.logger.info(f"Starting pipeline for: {filename}")
        
        try:
            # Step 1: OCR Processing
            if skip_ocr:
                # Try to load existing OCR result
                ocr_path = self.ocr_processor.get_ocr_output_path(file_path)
                if os.path.exists(ocr_path):
                    with open(ocr_path, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()
                    self.logger.info(f"Loaded existing OCR result from: {ocr_path}")
                    ocr_result = OCRResult(
                        file_path=file_path,
                        markdown_content=markdown_content,
                        page_count=0,
                        success=True
                    )
                else:
                    self.logger.warning(f"No existing OCR result found for {filename}, performing OCR")
                    ocr_result = self.ocr_processor.process_document(
                        file_path, 
                        save_markdown=self.config.save_ocr_markdown
                    )
            else:
                ocr_result = self.ocr_processor.process_document(
                    file_path, 
                    save_markdown=self.config.save_ocr_markdown
                )
            
            if not ocr_result.success:
                return False, f"OCR failed: {ocr_result.error_message}"
            
            # Step 2: Analyze markdown
            analysis = self.markdown_parser.analyze_markdown(ocr_result.markdown_content)
            self.logger.info(f"Analysis complete. Found {len(analysis['item_codes'])} item codes")
            
            # Step 3: Split markdown (optional)
            if self.config.split_by_item_code and analysis['item_codes']:
                sections = self.markdown_parser.split_by_item_code(ocr_result.markdown_content)
                
                # Save sections
                base_name = os.path.splitext(filename)[0]
                sections_subdir = os.path.join(self.config.sections_dir, base_name)
                self.markdown_parser.save_sections(sections, sections_subdir, base_name)
                
                # Parse each section
                text_items = [
                    (section.content, f"{base_name}_item_{section.item_code or idx}")
                    for idx, section in enumerate(sections, 1)
                ]
            else:
                # Parse entire document as one
                text_items = [(ocr_result.markdown_content, filename)]
            
            # Step 4: Parse with Gemini (multi-threaded if multiple sections)
            if len(text_items) > 1:
                parse_results = self.gemini_parser.parse_batch(
                    text_items, 
                    max_workers=self.config.max_workers
                )
            else:
                result = self.gemini_parser.parse_text(
                    text_items[0][0],
                    text_items[0][1],
                    save_output=True
                )
                parse_results = [result]
            
            # Check results
            successful = sum(1 for r in parse_results if r.success)
            failed = len(parse_results) - successful
            
            if failed > 0:
                self.logger.warning(f"Parsing completed with {failed} failures out of {len(parse_results)}")
            
            return True, f"Successfully processed {successful}/{len(parse_results)} sections"
            
        except Exception as e:
            self.logger.error(f"Pipeline failed for {filename}: {e}", exc_info=True)
            return False, str(e)
    
    def process_all_documents(self, skip_existing: bool = False) -> dict:
        """
        Process all documents in the input directory
        
        Args:
            skip_existing: Skip documents that already have structured output
            
        Returns:
            Dictionary with processing statistics
        """
        start_time = time.time()
        
        documents = self.find_documents()
        
        if not documents:
            self.logger.warning("No documents found to process")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'time_elapsed': 0
            }
        
        stats = {
            'total': len(documents),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'time_elapsed': 0
        }
        
        for doc_path in documents:
            filename = os.path.basename(doc_path)
            
            # Check if already processed
            if skip_existing:
                base_name = os.path.splitext(filename)[0]
                output_path = os.path.join(
                    self.config.structured_output_dir,
                    f"{base_name}_structured.json"
                )
                if os.path.exists(output_path):
                    self.logger.info(f"Skipping {filename} (already processed)")
                    stats['skipped'] += 1
                    continue
            
            # Process document
            success, message = self.process_single_document(doc_path)
            
            if success:
                stats['successful'] += 1
                self.logger.info(f"✓ {filename}: {message}")
            else:
                stats['failed'] += 1
                self.logger.error(f"✗ {filename}: {message}")
        
        stats['time_elapsed'] = time.time() - start_time
        
        return stats
    
    def print_summary(self, stats: dict):
        """Print processing summary"""
        summary = f"""
{'='*60}
{'DOCUMENT PROCESSING SUMMARY':^60}
{'='*60}
Total documents:     {stats['total']}
  ✓ Successful:      {stats['successful']}
  ✗ Failed:          {stats['failed']}
  → Skipped:         {stats['skipped']}

Time elapsed:        {stats['time_elapsed']:.2f} seconds
Average per doc:     {stats['time_elapsed']/max(stats['total'], 1):.2f} seconds
{'='*60}
"""
        print(summary)
        self.logger.info(summary)


def main():
    """Main entry point for the pipeline"""
    try:
        # Load configuration
        config = PipelineConfig.from_env()
        
        # Create pipeline
        pipeline = DocumentPipeline(config)
        
        # Process all documents
        stats = pipeline.process_all_documents(skip_existing=False)
        
        # Print summary
        pipeline.print_summary(stats)
        
    except Exception as e:
        print(f"ERROR: {e}")
        logging.error(f"Pipeline failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
