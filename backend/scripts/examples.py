"""
Example: Process a single document through the pipeline
"""
import os
from dotenv import load_dotenv
from pipeline import DocumentPipeline, PipelineConfig

# Load environment variables
load_dotenv()


def example_basic_usage():
    """Basic usage example - process all documents"""
    print("Example 1: Basic Pipeline Usage")
    print("-" * 50)
    
    # Create configuration from environment
    config = PipelineConfig.from_env()
    
    # Initialize pipeline
    pipeline = DocumentPipeline(config)
    
    # Process all documents
    stats = pipeline.process_all_documents()
    
    # Print summary
    pipeline.print_summary(stats)


def example_custom_config():
    """Example with custom configuration"""
    print("\nExample 2: Custom Configuration")
    print("-" * 50)
    
    config = PipelineConfig.from_env()
    
    # Customize settings
    config.max_workers = 3  # Reduce parallel workers
    config.split_by_item_code = True  # Enable splitting by item code
    config.save_ocr_markdown = True  # Save OCR results
    
    pipeline = DocumentPipeline(config)
    stats = pipeline.process_all_documents(skip_existing=True)
    
    pipeline.print_summary(stats)


def example_single_document():
    """Process a single document"""
    print("\nExample 3: Single Document Processing")
    print("-" * 50)
    
    config = PipelineConfig.from_env()
    pipeline = DocumentPipeline(config)
    
    # Find first document
    documents = pipeline.find_documents()
    
    if documents:
        doc_path = documents[0]
        print(f"Processing: {os.path.basename(doc_path)}")
        
        success, message = pipeline.process_single_document(doc_path)
        
        if success:
            print(f"✓ Success: {message}")
        else:
            print(f"✗ Failed: {message}")
    else:
        print("No documents found in input directory")


def example_with_analysis():
    """Process with detailed analysis"""
    print("\nExample 4: Processing with Analysis")
    print("-" * 50)
    
    from markdown_parser import MarkdownParser
    import logging
    
    config = PipelineConfig.from_env()
    pipeline = DocumentPipeline(config)
    
    # Get markdown parser
    parser = MarkdownParser(logging.getLogger("Example"))
    
    # Find and process first document
    documents = pipeline.find_documents()
    
    if documents:
        doc_path = documents[0]
        
        # Process OCR
        ocr_result = pipeline.ocr_processor.process_document(doc_path, save_markdown=True)
        
        if ocr_result.success:
            # Analyze markdown
            analysis = parser.analyze_markdown(ocr_result.markdown_content)
            
            print(f"\nDocument Analysis:")
            print(f"  Total Lines: {analysis['total_lines']}")
            print(f"  Total Characters: {analysis['total_chars']}")
            print(f"  Item Codes Found: {analysis['item_codes']}")
            print(f"  Sheet Numbers: {analysis['sheet_numbers']}")
            print(f"  Has Tables: {analysis['has_tables']}")
            print(f"  Estimated Sections: {analysis['estimated_sections']}")
            
            # Split by item code
            if analysis['item_codes']:
                sections = parser.split_by_item_code(ocr_result.markdown_content)
                print(f"\nSplit into {len(sections)} sections")
                
                for idx, section in enumerate(sections, 1):
                    print(f"  Section {idx}: {section.title} (Item Code: {section.item_code})")


def example_batch_parsing():
    """Example of batch parsing multiple markdown files"""
    print("\nExample 5: Batch Parsing")
    print("-" * 50)
    
    config = PipelineConfig.from_env()
    
    # Create text items to parse
    text_items = [
        ("Sample text 1 with tables...", "sample1"),
        ("Sample text 2 with items...", "sample2"),
        ("Sample text 3 with costs...", "sample3"),
    ]
    
    # Initialize Gemini parser
    from gemini_parser import GeminiParser
    import logging
    
    parser = GeminiParser(
        api_key=config.google_api_key,
        model_name=config.gemini_parser_model,
        output_dir=config.structured_output_dir,
        logger=logging.getLogger("GeminiParser")
    )
    
    # Parse in parallel
    print("Parsing multiple items in parallel...")
    # results = parser.parse_batch(text_items, max_workers=3)
    
    # Print results
    # for result in results:
    #     if result.success:
    #         print(f"✓ {result.source_file}: Success")
    #     else:
    #         print(f"✗ {result.source_file}: {result.error_message}")
    
    print("Note: Uncomment the parsing code to run actual batch parsing")


if __name__ == "__main__":
    print("=" * 60)
    print("Document Processing Pipeline - Examples")
    print("=" * 60)
    
    try:
        # Run examples
        example_basic_usage()
        # example_custom_config()
        # example_single_document()
        # example_with_analysis()
        # example_batch_parsing()
        
        print("\n" + "=" * 60)
        print("Examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
