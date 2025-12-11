"""
Pipeline Utilities
Helper functions for managing pipeline operations
"""
import os
import json
import argparse
from typing import Optional, List
from pathlib import Path


class PipelineManager:
    """Manage pipeline inputs, outputs, and results"""
    
    def __init__(self, base_dir: str = "/Users/chiru/Projects/Nexus/scripts"):
        self.base_dir = Path(base_dir)
        self.input_dir = self.base_dir / "input_documents"
        self.ocr_dir = self.base_dir / "ocr_results"
        self.sections_dir = self.base_dir / "markdown_sections"
        self.output_dir = self.base_dir / "output_structured"
    
    def list_inputs(self) -> List[str]:
        """List all input documents"""
        if not self.input_dir.exists():
            return []
        
        files = []
        for ext in ['.pdf', '.png', '.jpg', '.jpeg']:
            files.extend([f.name for f in self.input_dir.glob(f"*{ext}")])
        
        return sorted(files)
    
    def list_ocr_results(self) -> List[str]:
        """List all OCR markdown results"""
        if not self.ocr_dir.exists():
            return []
        
        return sorted([f.name for f in self.ocr_dir.glob("*.md")])
    
    def list_structured_outputs(self) -> List[str]:
        """List all structured JSON outputs"""
        if not self.output_dir.exists():
            return []
        
        return sorted([f.name for f in self.output_dir.glob("*.json")])
    
    def get_processing_status(self) -> dict:
        """Get overall processing status"""
        inputs = self.list_inputs()
        ocr_results = self.list_ocr_results()
        outputs = self.list_structured_outputs()
        
        # Match inputs to outputs
        processed = []
        pending = []
        
        for input_file in inputs:
            base_name = Path(input_file).stem
            output_name = f"{base_name}_structured.json"
            
            if output_name in outputs:
                processed.append(input_file)
            else:
                pending.append(input_file)
        
        return {
            'total_inputs': len(inputs),
            'total_ocr_results': len(ocr_results),
            'total_outputs': len(outputs),
            'processed': processed,
            'pending': pending
        }
    
    def view_structured_output(self, filename: str, show_items: bool = True) -> Optional[dict]:
        """View a structured output file"""
        filepath = self.output_dir / filename
        
        if not filepath.exists():
            print(f"File not found: {filename}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n{'='*70}")
        print(f"File: {filename}")
        print(f"{'='*70}")
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"Item Code: {data.get('item_code', 'N/A')}")
        print(f"Total Items: {len(data.get('items', []))}")
        
        if show_items and 'items' in data:
            print(f"\n{'Items:':-^70}")
            for idx, item in enumerate(data['items'][:10], 1):  # Show first 10
                print(f"\n{idx}. {item.get('description', 'N/A')}")
                print(f"   Unit: {item.get('unit', 'N/A')} | Qty: {item.get('quantity', 0)} | Total: ₹{item.get('total_cost', 0):,.2f}")
                
                if item.get('components'):
                    print(f"   → {len(item['components'])} sub-components")
            
            if len(data['items']) > 10:
                print(f"\n   ... and {len(data['items']) - 10} more items")
        
        if 'summary' in data and data['summary']:
            print(f"\n{'Cost Summary:':-^70}")
            for key, value in data['summary'].items():
                if value is not None:
                    print(f"{key.replace('_', ' ').title()}: ₹{value:,.2f}")
        
        print(f"{'='*70}\n")
        
        return data
    
    def view_ocr_result(self, filename: str, max_lines: int = 50) -> Optional[str]:
        """View an OCR markdown result"""
        filepath = self.ocr_dir / filename
        
        if not filepath.exists():
            print(f"File not found: {filename}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        print(f"\n{'='*70}")
        print(f"File: {filename}")
        print(f"Total Lines: {len(lines)}")
        print(f"{'='*70}")
        
        # Show first N lines
        preview_lines = lines[:max_lines]
        print('\n'.join(preview_lines))
        
        if len(lines) > max_lines:
            print(f"\n... ({len(lines) - max_lines} more lines)")
        
        print(f"{'='*70}\n")
        
        return content
    
    def clean_outputs(self, confirm: bool = False):
        """Clean all output directories"""
        if not confirm:
            print("Are you sure you want to delete all outputs? Use --confirm flag")
            return
        
        import shutil
        
        dirs_to_clean = [self.ocr_dir, self.sections_dir, self.output_dir]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"Cleaned: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)
        
        print("All outputs cleaned!")
    
    def create_directories(self):
        """Create all necessary directories"""
        dirs = [self.input_dir, self.ocr_dir, self.sections_dir, self.output_dir]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"Created: {dir_path}")


def main():
    """Command-line interface for pipeline utilities"""
    parser = argparse.ArgumentParser(description="Manage document processing pipeline")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show processing status')
    
    # List commands
    subparsers.add_parser('list-inputs', help='List input documents')
    subparsers.add_parser('list-ocr', help='List OCR results')
    subparsers.add_parser('list-outputs', help='List structured outputs')
    
    # View commands
    view_output_parser = subparsers.add_parser('view-output', help='View structured output')
    view_output_parser.add_argument('filename', help='Output filename')
    view_output_parser.add_argument('--no-items', action='store_true', help='Hide items list')
    
    view_ocr_parser = subparsers.add_parser('view-ocr', help='View OCR result')
    view_ocr_parser.add_argument('filename', help='OCR filename')
    view_ocr_parser.add_argument('--lines', type=int, default=50, help='Max lines to show')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean all outputs')
    clean_parser.add_argument('--confirm', action='store_true', help='Confirm deletion')
    
    # Setup command
    subparsers.add_parser('setup', help='Create necessary directories')
    
    args = parser.parse_args()
    
    manager = PipelineManager()
    
    if args.command == 'status':
        status = manager.get_processing_status()
        print(f"\n{'Pipeline Status':-^70}")
        print(f"Total Input Documents: {status['total_inputs']}")
        print(f"OCR Results Available: {status['total_ocr_results']}")
        print(f"Structured Outputs: {status['total_outputs']}")
        print(f"\nProcessed: {len(status['processed'])} documents")
        print(f"Pending: {len(status['pending'])} documents")
        
        if status['pending']:
            print(f"\nPending files:")
            for f in status['pending']:
                print(f"  - {f}")
    
    elif args.command == 'list-inputs':
        files = manager.list_inputs()
        print(f"\nInput Documents ({len(files)}):")
        for f in files:
            print(f"  - {f}")
    
    elif args.command == 'list-ocr':
        files = manager.list_ocr_results()
        print(f"\nOCR Results ({len(files)}):")
        for f in files:
            print(f"  - {f}")
    
    elif args.command == 'list-outputs':
        files = manager.list_structured_outputs()
        print(f"\nStructured Outputs ({len(files)}):")
        for f in files:
            print(f"  - {f}")
    
    elif args.command == 'view-output':
        manager.view_structured_output(args.filename, show_items=not args.no_items)
    
    elif args.command == 'view-ocr':
        manager.view_ocr_result(args.filename, max_lines=args.lines)
    
    elif args.command == 'clean':
        manager.clean_outputs(confirm=args.confirm)
    
    elif args.command == 'setup':
        manager.create_directories()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
