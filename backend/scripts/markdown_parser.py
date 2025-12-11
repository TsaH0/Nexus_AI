"""
Markdown Parser Module
Analyzes and splits large markdown files into manageable chunks
"""
import os
import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class MarkdownSection:
    """Represents a section of a markdown document"""
    title: str
    content: str
    section_number: Optional[str] = None
    item_code: Optional[str] = None
    start_line: int = 0
    end_line: int = 0


class MarkdownParser:
    """Parses and splits markdown documents into logical sections"""
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize Markdown Parser
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        
        # Patterns for detecting sections
        self.item_code_pattern = re.compile(r'Item\s+Code\s+No[.:]?\s*(\d+)', re.IGNORECASE)
        self.title_pattern = re.compile(r'^#+\s+(.+)$', re.MULTILINE)
        self.cost_data_pattern = re.compile(r'Cost\s+data\s+for\s+(.+)', re.IGNORECASE)
        self.sheet_pattern = re.compile(r'Sheet\s+No[.:]?\s*(\d+)', re.IGNORECASE)
        
    def analyze_markdown(self, markdown_content: str) -> Dict[str, any]:
        """
        Analyze markdown content to extract metadata
        
        Args:
            markdown_content: The markdown content to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        lines = markdown_content.split('\n')
        
        analysis = {
            'total_lines': len(lines),
            'total_chars': len(markdown_content),
            'item_codes': [],
            'sheet_numbers': [],
            'has_tables': False,
            'estimated_sections': 0
        }
        
        # Find item codes
        item_codes = self.item_code_pattern.findall(markdown_content)
        analysis['item_codes'] = list(set(item_codes))
        
        # Find sheet numbers
        sheet_numbers = self.sheet_pattern.findall(markdown_content)
        analysis['sheet_numbers'] = list(set(sheet_numbers))
        
        # Check for tables
        analysis['has_tables'] = '|' in markdown_content or 'Sr.No' in markdown_content
        
        # Estimate sections (based on headers and item codes)
        headers = self.title_pattern.findall(markdown_content)
        analysis['estimated_sections'] = len(headers) + len(item_codes)
        
        self.logger.info(f"Markdown Analysis: {analysis}")
        return analysis
    
    def split_by_item_code(self, markdown_content: str) -> List[MarkdownSection]:
        """
        Split markdown content by item codes
        
        Args:
            markdown_content: The markdown content to split
            
        Returns:
            List of MarkdownSection objects
        """
        sections = []
        lines = markdown_content.split('\n')
        
        current_content = []
        current_item_code = None
        current_title = None
        start_line = 0
        
        for i, line in enumerate(lines):
            # Check for item code
            item_code_match = self.item_code_pattern.search(line)
            if item_code_match:
                # Save previous section if exists
                if current_item_code is not None and current_content:
                    sections.append(MarkdownSection(
                        title=current_title or f"Item Code {current_item_code}",
                        content='\n'.join(current_content),
                        item_code=current_item_code,
                        start_line=start_line,
                        end_line=i
                    ))
                
                # Start new section
                current_item_code = item_code_match.group(1)
                current_content = [line]
                start_line = i
                current_title = None
            
            # If we have an active section, add content to it
            elif current_item_code is not None:
                current_content.append(line)
                
                # Check for title if not found yet
                if not current_title:
                    cost_match = self.cost_data_pattern.search(line)
                    if cost_match:
                        current_title = cost_match.group(1).strip()
        
        # Add the last section
        if current_item_code is not None and current_content:
            sections.append(MarkdownSection(
                title=current_title or f"Item Code {current_item_code}",
                content='\n'.join(current_content),
                item_code=current_item_code,
                start_line=start_line,
                end_line=len(lines)
            ))
        
        self.logger.info(f"Split markdown into {len(sections)} sections by item code")
        return sections
    
    def split_by_size(self, markdown_content: str, max_lines: int = 500) -> List[MarkdownSection]:
        """
        Split markdown content by size (number of lines)
        
        Args:
            markdown_content: The markdown content to split
            max_lines: Maximum lines per section
            
        Returns:
            List of MarkdownSection objects
        """
        sections = []
        lines = markdown_content.split('\n')
        
        for i in range(0, len(lines), max_lines):
            chunk = lines[i:i + max_lines]
            sections.append(MarkdownSection(
                title=f"Section {len(sections) + 1}",
                content='\n'.join(chunk),
                start_line=i,
                end_line=min(i + max_lines, len(lines))
            ))
        
        self.logger.info(f"Split markdown into {len(sections)} sections by size ({max_lines} lines each)")
        return sections
    
    def save_sections(self, sections: List[MarkdownSection], output_dir: str, base_filename: str):
        """
        Save markdown sections to separate files
        
        Args:
            sections: List of MarkdownSection objects to save
            output_dir: Directory to save sections
            base_filename: Base filename for the sections
        """
        os.makedirs(output_dir, exist_ok=True)
        
        for idx, section in enumerate(sections, 1):
            # Create filename
            if section.item_code:
                filename = f"{base_filename}_item_{section.item_code}.md"
            else:
                filename = f"{base_filename}_section_{idx:03d}.md"
            
            filepath = os.path.join(output_dir, filename)
            
            # Write section content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {section.title}\n\n")
                if section.item_code:
                    f.write(f"**Item Code:** {section.item_code}\n\n")
                f.write(f"**Lines:** {section.start_line} - {section.end_line}\n\n")
                f.write("---\n\n")
                f.write(section.content)
            
            self.logger.info(f"Saved section to: {filepath}")
    
    def extract_tables(self, markdown_content: str) -> List[Dict[str, any]]:
        """
        Extract tables from markdown content
        
        Args:
            markdown_content: The markdown content to extract tables from
            
        Returns:
            List of table dictionaries with metadata
        """
        tables = []
        lines = markdown_content.split('\n')
        
        in_table = False
        current_table = []
        table_start = 0
        
        for i, line in enumerate(lines):
            # Detect table rows (lines with | separators)
            if '|' in line and line.strip().startswith('|'):
                if not in_table:
                    in_table = True
                    table_start = i
                current_table.append(line)
            else:
                if in_table and current_table:
                    # Table ended
                    tables.append({
                        'start_line': table_start,
                        'end_line': i - 1,
                        'content': '\n'.join(current_table),
                        'row_count': len(current_table)
                    })
                    current_table = []
                in_table = False
        
        # Add last table if exists
        if current_table:
            tables.append({
                'start_line': table_start,
                'end_line': len(lines) - 1,
                'content': '\n'.join(current_table),
                'row_count': len(current_table)
            })
        
        self.logger.info(f"Extracted {len(tables)} tables from markdown")
        return tables
