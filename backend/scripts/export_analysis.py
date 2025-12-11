#!/usr/bin/env python3
"""
Export structured JSON data to CSV for analysis
Creates summary tables for:
- All items with pricing
- Raw materials categorization
- Procurement recommendations based on material type
"""
import os
import json
import csv
from pathlib import Path
from typing import List, Dict
import sys


# Material categories and their procurement characteristics
MATERIAL_CATEGORIES = {
    'steel': {
        'keywords': ['steel', 'ms', 'rebar', 'rod', 'angle', 'channel', 'beam', 'rsj', 'girder', 'plate', 'strip'],
        'shelf_life': 'Long (>5 years)',
        'reorder_frequency': 'Quarterly',
        'procurement_lead_time': '2-3 weeks'
    },
    'cement': {
        'keywords': ['cement', 'concrete', 'mortar'],
        'shelf_life': 'Medium (3-6 months)',
        'reorder_frequency': 'Monthly',
        'procurement_lead_time': '1 week'
    },
    'electrical': {
        'keywords': ['cable', 'wire', 'conductor', 'transformer', 'switchgear', 'panel', 'breaker', 'fuse'],
        'shelf_life': 'Long (>5 years)',
        'reorder_frequency': 'As needed',
        'procurement_lead_time': '2-4 weeks'
    },
    'paint': {
        'keywords': ['paint', 'coating', 'enamel', 'primer'],
        'shelf_life': 'Short (6-12 months)',
        'reorder_frequency': 'Monthly',
        'procurement_lead_time': '3-5 days'
    },
    'fasteners': {
        'keywords': ['bolt', 'nut', 'screw', 'washer', 'rivet', 'nail'],
        'shelf_life': 'Long (>5 years)',
        'reorder_frequency': 'Quarterly',
        'procurement_lead_time': '1 week'
    },
    'lumber': {
        'keywords': ['wood', 'timber', 'plywood', 'board'],
        'shelf_life': 'Medium (1-2 years)',
        'reorder_frequency': 'Bi-monthly',
        'procurement_lead_time': '1-2 weeks'
    },
    'insulation': {
        'keywords': ['insulation', 'insulator', 'foam', 'fiberglass'],
        'shelf_life': 'Long (>5 years)',
        'reorder_frequency': 'As needed',
        'procurement_lead_time': '1-2 weeks'
    },
    'pipes': {
        'keywords': ['pipe', 'tube', 'conduit', 'duct'],
        'shelf_life': 'Long (>5 years)',
        'reorder_frequency': 'As needed',
        'procurement_lead_time': '2-3 weeks'
    },
    'other': {
        'keywords': [],
        'shelf_life': 'Variable',
        'reorder_frequency': 'As needed',
        'procurement_lead_time': '1-2 weeks'
    }
}


def categorize_material(description: str) -> str:
    """Categorize material based on description"""
    desc_lower = description.lower()
    
    for category, info in MATERIAL_CATEGORIES.items():
        if category == 'other':
            continue
        for keyword in info['keywords']:
            if keyword in desc_lower:
                return category
    
    return 'other'


def export_to_csv(structured_output_dir: str, output_csv: str):
    """
    Export all structured JSON files to a single CSV
    
    Args:
        structured_output_dir: Directory containing *_structured.json files
        output_csv: Path to output CSV file
    """
    print(f"\n{'='*60}")
    print("EXPORTING STRUCTURED DATA TO CSV")
    print(f"{'='*60}")
    
    # Find all structured JSON files
    json_files = list(Path(structured_output_dir).glob('*_structured.json'))
    
    if not json_files:
        print(f"❌ No structured JSON files found in {structured_output_dir}")
        return False
    
    print(f"Found {len(json_files)} structured JSON files")
    
    # Collect all items
    all_items = []
    total_items = 0
    total_components = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            item_code = data.get('item_code', 'unknown')
            title = data.get('title', '')
            
            # Process main items
            for item in data.get('items', []):
                material_category = categorize_material(item['description'])
                category_info = MATERIAL_CATEGORIES[material_category]
                
                item_row = {
                    'item_code': item_code,
                    'project_title': title,
                    'serial_number': item.get('serial_number', ''),
                    'description': item.get('description', ''),
                    'unit': item.get('unit', ''),
                    'quantity': item.get('quantity', 0),
                    'rate_per_unit': item.get('rate_per_unit', 0) or 0,
                    'total_cost': item.get('total_cost', 0),
                    'material_category': material_category,
                    'shelf_life': category_info['shelf_life'],
                    'reorder_frequency': category_info['reorder_frequency'],
                    'procurement_lead_time': category_info['procurement_lead_time'],
                    'has_components': 'Yes' if item.get('components') else 'No',
                    'component_count': len(item.get('components') or [])
                }
                all_items.append(item_row)
                total_items += 1
                
                # Process components (sub-materials)
                if item.get('components'):
                    for comp in item['components']:
                        comp_category = categorize_material(comp['description'])
                        comp_category_info = MATERIAL_CATEGORIES[comp_category]
                        
                        comp_row = {
                            'item_code': item_code,
                            'project_title': title,
                            'serial_number': f"{item.get('serial_number', '')}-SUB",
                            'description': comp.get('description', ''),
                            'unit': comp.get('unit', ''),
                            'quantity': comp.get('quantity', 0),
                            'rate_per_unit': comp.get('rate_per_unit', 0) or 0,
                            'total_cost': comp.get('total_cost', 0),
                            'material_category': comp_category,
                            'shelf_life': comp_category_info['shelf_life'],
                            'reorder_frequency': comp_category_info['reorder_frequency'],
                            'procurement_lead_time': comp_category_info['procurement_lead_time'],
                            'has_components': 'No',
                            'component_count': 0
                        }
                        all_items.append(comp_row)
                        total_components += 1
        
        except Exception as e:
            print(f"  ⚠️  Error reading {json_file.name}: {e}")
    
    if not all_items:
        print("❌ No items extracted")
        return False
    
    # Write to CSV
    fieldnames = [
        'item_code', 'project_title', 'serial_number', 'description', 'unit', 
        'quantity', 'rate_per_unit', 'total_cost', 
        'material_category', 'shelf_life', 'reorder_frequency', 'procurement_lead_time',
        'has_components', 'component_count'
    ]
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_items)
    
    print(f"\n{'='*60}")
    print("EXPORT SUMMARY:")
    print(f"{'='*60}")
    print(f"  ✓ Total JSON files processed: {len(json_files)}")
    print(f"  ✓ Total main items: {total_items}")
    print(f"  ✓ Total sub-components: {total_components}")
    print(f"  ✓ Total rows in CSV: {len(all_items)}")
    print(f"  ")
    print(f"  📊 Output file: {output_csv}")
    print(f"  ")
    
    # Category breakdown
    print("  Material Categories:")
    category_counts = {}
    for item in all_items:
        cat = item['material_category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {cat.capitalize()}: {count} items")
    
    print(f"{'='*60}")
    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python export_analysis.py <structured_output_dir> [output.csv]")
        print("\nExample:")
        print("  python export_analysis.py output_structured materials_analysis.csv")
        return 1
    
    structured_output_dir = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) >= 3 else 'materials_analysis.csv'
    
    if not os.path.exists(structured_output_dir):
        print(f"❌ Directory not found: {structured_output_dir}")
        return 1
    
    success = export_to_csv(structured_output_dir, output_csv)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
