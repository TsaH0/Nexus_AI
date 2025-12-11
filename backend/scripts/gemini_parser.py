"""
Gemini Parser Module
Uses Google Gemini with multi-threading to extract structured data
"""
import os
import json
import logging
import threading
from typing import Optional, List
import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError
from dataclasses import dataclass


# Pydantic Models for Structured Output
class SubComponent(BaseModel):
    """Sub-component in a bill of materials"""
    description: str = Field(description="Description of the material in the sub-table.")
    unit: Optional[str] = Field(None)
    quantity: float
    rate_per_unit: Optional[float] = Field(None, alias="rt_u_rs")
    total_cost: float = Field(alias="amt_rs")
    
    class Config:
        populate_by_name = True


class Item(BaseModel):
    """Main item in a bill of quantities"""
    serial_number: int | str
    description: str
    unit: Optional[str] = None
    quantity: float
    rate_per_unit: Optional[float] = None
    total_cost: float
    components: Optional[List[SubComponent]] = Field(
        None, 
        description="Detailed breakdown from a 'Sheet' table."
    )


class CostSummary(BaseModel):
    """Cost summary for the entire bill"""
    cost_of_material: Optional[float] = None
    service_cost: Optional[float] = None
    sub_total: Optional[float] = None
    turnkey_charges: Optional[float] = None
    total_cost_of_estimate: Optional[float] = None
    civil_works_cost: Optional[float] = None


class BillOfQuantities(BaseModel):
    """Complete bill of quantities structure"""
    title: str = Field(description="The main title of the cost estimate.")
    item_code: Optional[str] = Field(None)
    items: List[Item]
    summary: CostSummary


@dataclass
class ParseResult:
    """Result from parsing operation"""
    source_file: str
    success: bool
    structured_data: Optional[BillOfQuantities] = None
    error_message: Optional[str] = None
    raw_response: Optional[str] = None


class GeminiParser:
    """Handles structured data extraction using Google Gemini"""
    
    def __init__(
        self, 
        api_key: str, 
        model_name: str, 
        output_dir: str,
        logger: logging.Logger,
        generation_config: Optional[dict] = None
    ):
        """
        Initialize Gemini Parser
        
        Args:
            api_key: Google API key
            model_name: Gemini model name
            output_dir: Directory to save structured outputs
            logger: Logger instance
            generation_config: Optional generation configuration
        """
        if not api_key:
            raise ValueError("Google API key is required.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        self.output_dir = output_dir
        self.logger = logger
        
        self.generation_config = generation_config or {
            "temperature": 0.0,  # Zero temperature for deterministic output
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,  # Reduced for reliability - focus on getting data out
        }
        
        # Configure safety settings to be permissive for technical content
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.logger.info(f"GeminiParser initialized with model '{self.model_name}'.")
        self.logger.info(f"Structured outputs will be saved to: {self.output_dir}")
    
    def _repair_json(self, json_str: str, source_file: str, thread_name: str) -> str:
        """
        Attempt to repair common JSON issues from truncated or malformed responses
        
        Args:
            json_str: JSON string to repair
            source_file: Source filename for logging
            thread_name: Thread name for logging
            
        Returns:
            Repaired JSON string
        """
        import re
        
        if not json_str:
            return json_str
            
        original = json_str
        repairs_made = []
        
        # 1. Strip any markdown code blocks if present
        if json_str.strip().startswith('```'):
            json_str = re.sub(r'^```(?:json)?\s*', '', json_str.strip())
            json_str = re.sub(r'\s*```$', '', json_str.strip())
            repairs_made.append("Removed markdown code blocks")
        
        # 2. Find the actual JSON object (starts with { ends with })
        first_brace = json_str.find('{')
        if first_brace > 0:
            json_str = json_str[first_brace:]
            repairs_made.append("Trimmed content before first brace")
        elif first_brace == -1:
            # No JSON object found
            repairs_made.append("No JSON object found")
            return json_str
        
        # 3. Remove trailing commas (,} or ,])
        original_len = len(json_str)
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        if len(json_str) != original_len:
            repairs_made.append("Removed trailing commas")
        
        # 4. Fix truncated incomplete objects at end of arrays
        # Pattern: , { incomplete... at end
        json_str = re.sub(r',\s*\{[^{}]*$', '', json_str)
        
        # 5. Fix incomplete field values
        # Pattern: "key": followed by nothing or incomplete
        json_str = re.sub(r'("[\w_]+")\s*:\s*$', r'\1: null', json_str)
        json_str = re.sub(r'("[\w_]+")\s*:\s*,', r'\1: null,', json_str)
        
        # 6. Fix unterminated strings line by line
        lines = json_str.split('\n')
        repaired_lines = []
        for i, line in enumerate(lines):
            # Count unescaped quotes
            quote_count = len(re.findall(r'(?<!\\)"', line))
            if quote_count % 2 != 0:
                # Try to close the string properly
                stripped = line.rstrip()
                if not stripped.endswith(('"', ',', '{', '[', ':', '}', ']')):
                    line = stripped + '"'
                    repairs_made.append(f"Closed string on line {i+1}")
            repaired_lines.append(line)
        json_str = '\n'.join(repaired_lines)
        
        # 7. Remove trailing commas again after other repairs
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 8. Handle truncation - find last complete value
        json_str = json_str.rstrip()
        
        # Remove trailing incomplete content that's not a valid ending
        while json_str and not json_str[-1] in '}]"0123456789nulltruefalse'[-1:]:
            # Check for valid endings
            if json_str.endswith(('null', 'true', 'false')):
                break
            if json_str[-1].isdigit():
                break
            if json_str[-1] in '}]"':
                break
            # Remove last character
            json_str = json_str[:-1].rstrip()
            
        # 9. Balance braces and brackets
        brace_count = json_str.count('{') - json_str.count('}')
        bracket_count = json_str.count('[') - json_str.count(']')
        
        # Close arrays first (they're nested inside objects)
        if bracket_count > 0:
            # Remove any trailing comma before closing
            json_str = re.sub(r',\s*$', '', json_str)
            json_str += ']' * bracket_count
            repairs_made.append(f"Added {bracket_count} closing bracket(s)")
        
        # Then close objects
        if brace_count > 0:
            json_str = re.sub(r',\s*$', '', json_str)
            json_str += '}' * brace_count
            repairs_made.append(f"Added {brace_count} closing brace(s)")
        
        # 10. Final cleanup of trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 11. Try to parse - if it fails, try more aggressive repair
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            repairs_made.append(f"Still invalid at pos {e.pos}: {e.msg}")
            
            # Handle specific error types
            if "Expecting ',' delimiter" in e.msg:
                # This often means duplicate keys or missing commas
                # Try to find and fix the error position
                error_pos = e.pos
                
                # Find the context around the error
                start = max(0, error_pos - 50)
                end = min(len(json_str), error_pos + 50)
                context = json_str[start:end]
                
                # Check if there's a missing comma between objects/arrays
                if error_pos < len(json_str):
                    char_before = json_str[error_pos - 1] if error_pos > 0 else ''
                    char_at = json_str[error_pos] if error_pos < len(json_str) else ''
                    
                    # Insert comma if needed between } and { or ] and [
                    if char_before in '}]' and char_at in '{["':
                        json_str = json_str[:error_pos] + ',' + json_str[error_pos:]
                        repairs_made.append("Added missing comma between elements")
                
            # Try to truncate to last valid item
            # Look for pattern: }, followed by incomplete content
            last_complete = None
            
            # Find positions of all complete item closings in arrays
            for match in re.finditer(r'\}\s*(?=,|\])', json_str):
                if match.end() < e.pos:  # Only consider positions before error
                    last_complete = match.end()
            
            if last_complete and last_complete < len(json_str) - 10:
                # Truncate and rebalance
                json_str = json_str[:last_complete]
                repairs_made.append(f"Truncated to position {last_complete}")
                
                # Remove trailing comma if present
                json_str = re.sub(r',\s*$', '', json_str)
                
                # Rebalance after truncation
                brace_count = json_str.count('{') - json_str.count('}')
                bracket_count = json_str.count('[') - json_str.count(']')
                
                if bracket_count > 0:
                    json_str += ']' * bracket_count
                if brace_count > 0:
                    json_str += '}' * brace_count
                
                # Final trailing comma cleanup
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        if repairs_made:
            self.logger.info(f"[{thread_name}] JSON repairs for {source_file}: {', '.join(repairs_made[:5])}")
        
        return json_str
    
    def create_extraction_prompt(self, raw_text: str, simplified: bool = False) -> str:
        """
        Create a prompt for data extraction
        
        Args:
            raw_text: Raw markdown/text content to parse
            simplified: If True, use a minimal prompt for retry attempts
            
        Returns:
            Formatted prompt string
        """
        schema = BillOfQuantities.model_json_schema()
        
        if simplified:
            # Minimal prompt for retry attempts - focuses on structure only
            return f"""Extract structured JSON from this Bill of Quantities text.

SCHEMA: {json.dumps(schema)}

RULES:
- Return ONLY valid JSON matching schema
- Extract item_code from "Item Code No. XXXX"
- Extract title after item code
- Main table rows -> items array
- "as per sheet X" -> find sheet table -> components array
- Summary costs -> summary object
- Use null for missing optional fields
- NO markdown, NO explanations

TEXT:
{raw_text}

JSON:"""
        
        # Standard compact prompt
        prompt = f"""Extract Bill of Quantities data to JSON. Follow schema EXACTLY.

**SCHEMA:**
```json
{json.dumps(schema, indent=2)}
```

**EXTRACTION RULES:**
1. item_code: Extract from "Item Code No. XXXX" (e.g., "1018")
2. title: Text after item code describing the work
3. items: Each row from main table (S.N., Description, Unit, Qty, Rate, Amount)
4. components: If item references "sheet A/B/X", find that sheet table and extract its rows
5. summary: Extract Cost of Material, Service Cost, Sub-Total, Total/Tender Cost

**FORMAT:**
- Return ONLY valid JSON
- NO markdown code blocks
- NO explanations
- Preserve exact numbers
- Use null for missing optional fields

**TEXT TO PARSE:**
{raw_text}

**JSON OUTPUT:**"""
        return prompt
    
    def parse_text(
        self, 
        raw_text: str, 
        source_file: str,
        save_output: bool = True,
        max_retries: int = 2
    ) -> ParseResult:
        """
        Parse raw text to structured BillOfQuantities model with retry logic
        
        Args:
            raw_text: Raw text content to parse
            source_file: Source filename for logging
            save_output: Whether to save the structured output
            max_retries: Maximum number of retry attempts
            
        Returns:
            ParseResult object
        """
        import time
        
        thread_name = threading.current_thread().name
        self.logger.info(f"[{thread_name}] Starting Gemini parsing for {source_file} ({len(raw_text)} chars)")
        
        # If content is too large, truncate to first portion
        # This ensures we get SOME data rather than failing completely
        MAX_CHARS = 15000  # Conservative limit
        if len(raw_text) > MAX_CHARS:
            self.logger.warning(f"[{thread_name}] Content too large ({len(raw_text)} chars), truncating to {MAX_CHARS} chars")
            raw_text = raw_text[:MAX_CHARS] + "\n\n[Content truncated for processing]"
        
        last_error = None
        last_response = None
        all_responses = []  # Track all attempts for debugging
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    self.logger.info(f"[{thread_name}] Retry attempt {attempt + 1}/{max_retries} for {source_file} (waiting {wait_time}s)")
                    time.sleep(wait_time)
                
                # Use simplified prompt on first retry to reduce token usage
                use_simplified = attempt >= 1  # Start simplified earlier
                prompt = self.create_extraction_prompt(raw_text, simplified=use_simplified)
                
                if use_simplified:
                    self.logger.info(f"[{thread_name}] Using simplified prompt for {source_file}")
                
                # Generate response with increased timeout for large documents
                config = genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    **self.generation_config
                )
                
                response = self.model.generate_content(
                    prompt, 
                    generation_config=config,
                    safety_settings=self.safety_settings
                )
                
                # Check if response has valid parts before accessing text
                if not response.parts:
                    finish_reason = response.candidates[0].finish_reason if response.candidates else 'unknown'
                    prompt_feedback = getattr(response, 'prompt_feedback', None)
                    
                    error_details = f"Response has no parts - finish_reason: {finish_reason}"
                    if prompt_feedback:
                        error_details += f", prompt_feedback: {prompt_feedback}"
                    
                    self.logger.warning(f"[{thread_name}] Empty response for {source_file}: {error_details}")
                    raise ValueError(error_details)
                
                last_response = response.text
                all_responses.append({"attempt": attempt + 1, "response": last_response[:500]})
                
                # Check if response is complete (basic validation)
                if not last_response or len(last_response) < 50:
                    raise ValueError(f"Response too short ({len(last_response) if last_response else 0} chars), likely incomplete")
                
                # Try to repair common JSON issues
                last_response = self._repair_json(last_response, source_file, thread_name)
                
                # Validate with Pydantic
                validated_model = BillOfQuantities.model_validate_json(last_response)
                
                # Sanity check - ensure we have at least some data
                if not validated_model.items:
                    raise ValueError("Parsed model has no items - extraction may have failed")
                
                # Save output if requested
                if save_output:
                    base_name = os.path.splitext(os.path.basename(source_file))[0]
                    output_path = os.path.join(self.output_dir, f"{base_name}_structured.json")
                    
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(validated_model.model_dump_json(indent=2))
                    
                    self.logger.info(f"[{thread_name}] ✓ Saved: {output_path} ({len(validated_model.items)} items)")
                
                self.logger.info(f"[{thread_name}] ✓ Success for {source_file} (attempt {attempt + 1}, {len(validated_model.items)} items)")
                
                return ParseResult(
                    source_file=source_file,
                    success=True,
                    structured_data=validated_model
                )
                
            except ValidationError as e:
                last_error = f"Validation error: {str(e)[:200]}"
                self.logger.warning(f"[{thread_name}] ✗ Validation failed for {source_file} (attempt {attempt + 1})")
                
                if attempt < max_retries - 1:
                    self.logger.info(f"[{thread_name}] Will retry parsing for {source_file}")
                else:
                    self.logger.error(f"[{thread_name}] ✗ Final validation failure for {source_file}")
                    if last_response:
                        # Save the failed response for debugging
                        debug_path = os.path.join(self.output_dir, f"{source_file}_failed.json")
                        with open(debug_path, "w", encoding="utf-8") as f:
                            f.write(last_response)
                        self.logger.error(f"[{thread_name}] Failed response saved to: {debug_path}")
                
            except Exception as e:
                last_error = str(e)[:200]
                self.logger.warning(f"[{thread_name}] ✗ Gemini error for {source_file} (attempt {attempt + 1}): {str(e)[:100]}")
                
                if attempt < max_retries - 1:
                    self.logger.info(f"[{thread_name}] Will retry parsing for {source_file}")
                else:
                    self.logger.error(f"[{thread_name}] ✗ Final parsing failure for {source_file}")
        
        # All retries exhausted
        return ParseResult(
            source_file=source_file,
            success=False,
            error_message=f"Failed after {max_retries} attempts: {last_error}",
            raw_response=last_response
        )
    
    def parse_batch(
        self,
        text_items: List[tuple],  # List of (text, source_file) tuples
        max_workers: int = 5
    ) -> List[ParseResult]:
        """
        Parse multiple texts in parallel using threading
        
        Args:
            text_items: List of (text_content, source_filename) tuples
            max_workers: Maximum number of parallel threads
            
        Returns:
            List of ParseResult objects
        """
        import concurrent.futures
        from tqdm import tqdm
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_source = {
                executor.submit(self.parse_text, text, source, True): source
                for text, source in text_items
            }
            
            # Process completed tasks with progress bar
            for future in tqdm(
                concurrent.futures.as_completed(future_to_source),
                total=len(text_items),
                desc="Parsing documents"
            ):
                source = future_to_source[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    self.logger.error(f"Exception for {source}: {exc}")
                    results.append(ParseResult(
                        source_file=source,
                        success=False,
                        error_message=str(exc)
                    ))
        
        return results
