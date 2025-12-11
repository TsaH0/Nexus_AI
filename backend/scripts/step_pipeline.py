#!/usr/bin/env python3
"""
Step-by-step pipeline execution
Run OCR, then analysis, then Gemini parsing
"""
import os
import sys
from dotenv import load_dotenv
from pipeline import DocumentPipeline, PipelineConfig
from markdown_parser import MarkdownParser
import logging

# Load environment variables
load_dotenv()


def run_ocr_only():
    """Step 1: Run OCR on all documents"""
    print("Step 1: Running OCR on all documents...")
    print("-" * 50)

    config = PipelineConfig.from_env()
    pipeline = DocumentPipeline(config)

    documents = pipeline.find_documents()
    if not documents:
        print("No documents found!")
        return False

    success_count = 0
    for doc_path in documents:
        filename = os.path.basename(doc_path)
        print(f"Processing OCR for: {filename}")

        # Just run OCR part
        ocr_result = pipeline.ocr_processor.process_document(doc_path, save_markdown=True)

        if ocr_result.success:
            print(f"✓ OCR completed: {ocr_result.page_count} pages")
            success_count += 1
        else:
            print(f"✗ OCR failed: {ocr_result.error_message}")

    print(f"\nOCR completed: {success_count}/{len(documents)} documents")
    return success_count > 0


def run_analysis_only():
    """Step 2: Analyze OCR results"""
    print("\nStep 2: Analyzing OCR results...")
    print("-" * 50)

    config = PipelineConfig.from_env()
    pipeline = DocumentPipeline(config)

    # Find OCR markdown files
    ocr_files = []
    if os.path.exists(config.ocr_output_dir):
        ocr_files = [f for f in os.listdir(config.ocr_output_dir) if f.endswith('_ocr.md')]

    if not ocr_files:
        print("No OCR results found! Run OCR first.")
        return False

    parser = MarkdownParser(logging.getLogger("Analysis"))

    for ocr_file in ocr_files:
        ocr_path = os.path.join(config.ocr_output_dir, ocr_file)
        print(f"Analyzing: {ocr_file}")

        with open(ocr_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Analyze the markdown
        analysis = parser.analyze_markdown(content)

        print(f"  Lines: {analysis['total_lines']}")
        print(f"  Item codes: {analysis['item_codes']}")
        print(f"  Sheet numbers: {analysis['sheet_numbers']}")
        print(f"  Has tables: {analysis['has_tables']}")

        # Split into sections if item codes found
        if analysis['item_codes']:
            sections = parser.split_by_item_code(content)
            print(f"  Split into {len(sections)} sections")

            # Save sections
            base_name = ocr_file.replace('_ocr.md', '')
            sections_subdir = os.path.join(config.sections_dir, base_name)
            parser.save_sections(sections, sections_subdir, base_name)
            print(f"  Sections saved to: {sections_subdir}")

    print("\nAnalysis completed!")
    return True


def run_gemini_only():
    """Step 3: Run Gemini parsing on pre-split item code sections from analysis step"""
    print("\nStep 3: Running Gemini parsing on item code sections...")
    print("-" * 50)

    config = PipelineConfig.from_env()
    pipeline = DocumentPipeline(config)

    # Find markdown sections created by the analysis step
    sections_to_process = []

    if os.path.exists(config.sections_dir):
        for root, dirs, files in os.walk(config.sections_dir):
            for file in files:
                if file.endswith('.md'):
                    sections_to_process.append(os.path.join(root, file))

    if not sections_to_process:
        print("No sections found! Run 'python step_pipeline.py analysis' first.")
        return False

    print(f"Found {len(sections_to_process)} item code sections to process")

    # Prepare text items for batch processing
    text_items = []
    
    for section_path in sections_to_process:
        try:
            filename = os.path.basename(section_path)
            item_code = None
            
            if '_item_' in filename:
                item_code = filename.split('_item_')[1].replace('.md', '')
            
            with open(section_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract meaningful content (skip metadata headers)
            lines = content.split('\n')
            content_lines = []
            in_content = False

            for line in lines:
                if line.startswith('---'):
                    in_content = True
                    continue
                if in_content:
                    content_lines.append(line)

            content = '\n'.join(content_lines).strip()
            
            if content:
                source_name = f"item_{item_code}" if item_code else os.path.basename(section_path)
                text_items.append((content, source_name))
                print(f"  → Queued Item Code {item_code}: {len(content)} chars")

        except Exception as e:
            print(f"  ✗ Error reading {section_path}: {e}")

    if not text_items:
        print("No valid content found in sections!")
        return False

    print(f"\nProcessing {len(text_items)} item codes with Gemini (multi-threaded)...")
    print("-" * 50)
    
    # Parse with Gemini
    results = pipeline.gemini_parser.parse_batch(text_items, max_workers=config.max_workers)

    # Report results
    print("\nResults by Item Code:")
    success_count = 0
    for result in results:
        if result.success:
            success_count += 1
            print(f"  ✓ {result.source_file}: Success")
            if result.structured_data:
                print(f"    - Title: {result.structured_data.title}")
                print(f"    - Items extracted: {len(result.structured_data.items)}")
        else:
            print(f"  ✗ {result.source_file}: {result.error_message}")

    print("-" * 50)
    print(f"Gemini parsing completed: {success_count}/{len(results)} item codes processed")

    return success_count > 0


def run_gemini_whole_file(limit: int = 30):
    """Step 3 Alternative: Parse entire markdown files by splitting into item code chunks
    
    Args:
        limit: Optional limit on number of item codes to process (default: 30 for practical data collection)
    """
    print("\nStep 3 (Whole File): Parsing markdown files into item code chunks...")
    print("-" * 60)
    if limit:
        print(f"⚙️  Processing first {limit} item codes (for practical data collection)")

    config = PipelineConfig.from_env()
    pipeline = DocumentPipeline(config)
    
    from markdown_parser import MarkdownParser
    parser = MarkdownParser(logging.getLogger("MarkdownParser"))

    # Find entire OCR markdown files
    ocr_files = []
    if os.path.exists(config.ocr_output_dir):
        ocr_files = [f for f in os.listdir(config.ocr_output_dir) if f.endswith('_ocr.md')]

    if not ocr_files:
        print("No OCR markdown files found! Run OCR first.")
        return False

    print(f"Found {len(ocr_files)} markdown files to process")

    # Process each file: split by item codes, then parse each chunk
    all_text_items = []
    
    for ocr_file in ocr_files:
        ocr_path = os.path.join(config.ocr_output_dir, ocr_file)
        base_name = ocr_file.replace('_ocr.md', '')

        try:
            print(f"\n📄 Processing: {ocr_file}")
            
            with open(ocr_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Skip metadata header
            lines = content.split('\n')
            content_lines = []
            start_processing = False
            
            for line in lines:
                if line.startswith('---') and not start_processing:
                    start_processing = True
                    continue
                if start_processing:
                    content_lines.append(line)

            full_content = '\n'.join(content_lines).strip()
            print(f"  Total size: {len(full_content):,} characters")

            # Analyze and split by item codes
            analysis = parser.analyze_markdown(full_content)
            print(f"  Item codes found: {analysis['item_codes']}")
            
            if analysis['item_codes']:
                # Split by item code
                sections = parser.split_by_item_code(full_content)
                print(f"  Split into {len(sections)} item code sections")
                
                # Add each section as a separate text item for Gemini
                for idx, section in enumerate(sections, 1):
                    if section.content.strip():
                        item_code = section.item_code or f"section_{idx}"
                        source_name = f"{base_name}_item_{item_code}"
                        all_text_items.append((section.content, source_name))
                        print(f"    → Item {item_code}: {len(section.content):,} chars")
            else:
                # No item codes found, split by size
                print(f"  ⚠ No item codes found, splitting by size...")
                sections = parser.split_by_size(full_content, max_lines=500)
                print(f"  Split into {len(sections)} sections by size")
                
                for idx, section in enumerate(sections, 1):
                    if section.content.strip():
                        source_name = f"{base_name}_chunk_{idx}"
                        all_text_items.append((section.content, source_name))
                        print(f"    → Chunk {idx}: {len(section.content):,} chars")

        except Exception as e:
            print(f"  ✗ Error processing {ocr_path}: {e}")
            import traceback
            traceback.print_exc()

    if not all_text_items:
        print("\n❌ No valid content chunks extracted!")
        return False

    # Apply limit if specified
    if limit and limit < len(all_text_items):
        print(f"\n⚠ Limiting to first {limit} item codes (out of {len(all_text_items)})")
        all_text_items = all_text_items[:limit]

    print(f"\n{'='*60}")
    print(f"Total chunks to process: {len(all_text_items)}")
    print(f"Processing with Gemini (multi-threaded, max_workers={config.max_workers})...")
    print(f"{'='*60}\n")

    # Parse all chunks with Gemini
    results = pipeline.gemini_parser.parse_batch(all_text_items, max_workers=config.max_workers)

    # Report results with detailed summary
    print(f"\n{'='*60}")
    print("PROCESSING RESULTS:")
    print(f"{'='*60}")
    
    success_count = 0
    failed_items = []
    total_items_extracted = 0
    total_components_extracted = 0
    
    for result in results:
        if result.success:
            success_count += 1
            if result.structured_data:
                items_count = len(result.structured_data.items)
                components_count = sum(
                    len(item.components or []) 
                    for item in result.structured_data.items
                )
                total_items_extracted += items_count
                total_components_extracted += components_count
                print(f"  ✓ {result.source_file}: {items_count} items, {components_count} components")
        else:
            failed_items.append(result.source_file)
            error_short = (result.error_message or "Unknown error")[:80]
            print(f"  ✗ {result.source_file}: {error_short}")

    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    print(f"  Item Codes Processed: {len(results)}")
    print(f"  ✓ Successful: {success_count} ({100*success_count/len(results):.1f}%)")
    print(f"  ✗ Failed: {len(failed_items)} ({100*len(failed_items)/len(results):.1f}%)")
    print(f"  ")
    print(f"  Total Items Extracted: {total_items_extracted}")
    print(f"  Total Components Extracted: {total_components_extracted}")
    print(f"  Output Directory: {config.structured_output_dir}")
    
    if failed_items:
        print(f"\n  Failed Item Codes:")
        for item in failed_items[:10]:  # Show first 10
            print(f"    - {item}")
        if len(failed_items) > 10:
            print(f"    ... and {len(failed_items) - 10} more")
        print(f"\n  Tip: Check failed output files in: {config.structured_output_dir}")
    
    print(f"{'='*60}")

    return success_count > 0


def run_full_pipeline():
    """Run the complete pipeline"""
    print("Running full pipeline...")
    print("=" * 50)

    config = PipelineConfig.from_env()
    pipeline = DocumentPipeline(config)

    stats = pipeline.process_all_documents()
    pipeline.print_summary(stats)


def main():
    if len(sys.argv) < 2:
        print("Usage: python step_pipeline.py [ocr|analysis|gemini|gemini-whole|full] [options]")
        print("\nCommands:")
        print("  ocr              - Run OCR on documents")
        print("  analysis         - Analyze OCR results and split into sections")
        print("  gemini           - Run Gemini parsing on item code sections")
        print("  gemini-whole     - Run Gemini parsing on entire markdown files")
        print("  gemini-whole N   - Process only first N item codes (for testing)")
        print("  full             - Run complete pipeline")
        return 1

    command = sys.argv[1].lower()
    
    # Parse optional limit for gemini-whole
    limit = None
    if len(sys.argv) >= 3 and command == 'gemini-whole':
        try:
            limit = int(sys.argv[2])
        except ValueError:
            print(f"Invalid limit: {sys.argv[2]}")
            return 1

    try:
        if command == 'ocr':
            success = run_ocr_only()
        elif command == 'analysis':
            success = run_analysis_only()
        elif command == 'gemini':
            success = run_gemini_only()
        elif command == 'gemini-whole':
            success = run_gemini_whole_file(limit=limit)
        elif command == 'full':
            run_full_pipeline()
            return 0
        else:
            print(f"Unknown command: {command}")
            return 1

        if command != 'full':
            print(f"\nCommand '{command}' completed {'successfully' if success else 'with errors'}")

        return 0 if success else 1

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
