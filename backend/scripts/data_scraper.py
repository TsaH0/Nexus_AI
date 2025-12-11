import os
import logging
import json
import base64
import time
from typing import List, Optional, Union
from dataclasses import dataclass
import concurrent.futures
import threading

# --- Dependency Imports ---
from mistralai import Mistral 
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

# Load environment variables from a .env file
load_dotenv()

# ==============================================================================
#  1. CONFIGURATION: All settings in one place for easy modification
# ==============================================================================
class Config:
    # --- Model Selection ---
    MISTRAL_OCR_MODEL = "mistral-ocr-latest"
    GEMINI_PARSER_MODEL = "gemini-flash-latest" 

    # --- Directory Paths ---
    SOURCE_DIRECTORY = "/Users/chiru/Projects/Nexus/scripts/input_documents" 
    OUTPUT_DIRECTORY = "/Users/chiru/Projects/Nexus/scripts/output_structured"
    LOG_FILE_PATH = "processor.log"

    # --- Performance ---
    MAX_WORKERS = 5 # Number of parallel threads

# ==============================================================================
#  2. PYDANTIC MODELS (Defines the final, structured output)
# ==============================================================================
class SubComponent(BaseModel):
    description: str = Field(description="Description of the material in the sub-table.")
    unit: Optional[str] = Field(None)
    quantity: float
    rate_per_unit: Optional[float] = Field(None, alias="rt_u_rs")
    total_cost: float = Field(alias="amt_rs")
    class Config: populate_by_name = True

class Item(BaseModel):
    serial_number: Union[int, str]
    description: str
    unit: Optional[str] = None
    quantity: float
    rate_per_unit: Optional[float] = None
    total_cost: float
    components: Optional[List[SubComponent]] = Field(None, description="Detailed breakdown from a 'Sheet' table.")

class CostSummary(BaseModel):
    cost_of_material: Optional[float] = None; service_cost: Optional[float] = None; sub_total: Optional[float] = None;
    turnkey_charges: Optional[float] = None; total_cost_of_estimate: Optional[float] = None; civil_works_cost: Optional[float] = None

class BillOfQuantities(BaseModel):
    title: str = Field(description="The main title of the cost estimate.")
    item_code: Optional[str] = Field(None)
    items: List[Item]
    summary: CostSummary

# ==============================================================================
#  3. MISTRAL OCR PROCESSOR
# ==============================================================================
@dataclass
class OCRProcessorOutput: full_text: str
class MistralOCRProcessor:
    def __init__(self, api_key: str, model_name: str, logger: logging.Logger):
        if not api_key: raise ValueError("Mistral API key is required.")
        self.client = Mistral(api_key=api_key)
        self.ocr_model = model_name
        self.logger = logger
        self.logger.info(f"MistralOCRProcessor initialized with model '{self.ocr_model}'.")
    def process_document(self, file_path: str) -> OCRProcessorOutput | None:
        thread_name = threading.current_thread().name
        self.logger.info(f"[{thread_name}] Starting OCR for: {os.path.basename(file_path)}")
        try:
            with open(file_path, "rb") as f: file_bytes = f.read()
            file_data_b64 = base64.b64encode(file_bytes).decode("utf-8")
            ext = os.path.splitext(file_path)[1].lower()
            media_type = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}.get(ext, "application/octet-stream")
            ocr_response = self.client.ocr.process(model=self.ocr_model, document={"type": "document_url", "document_url": f"data:{media_type};base64,{file_data_b64}"})
            if not ocr_response.pages: self.logger.warning(f"[{thread_name}] OCR returned no pages for {os.path.basename(file_path)}."); return OCRProcessorOutput(full_text="")
            full_text = "\n\n".join([page.markdown for page in ocr_response.pages])
            self.logger.info(f"[{thread_name}] OCR Complete for {os.path.basename(file_path)}")
            return OCRProcessorOutput(full_text=full_text)
        except Exception as e: self.logger.error(f"[{thread_name}] OCR failed for {os.path.basename(file_path)}: {e}", exc_info=False); return None

# ==============================================================================
#  4. GEMINI DATA PARSER (with Few-Shot Prompt)
# ==============================================================================
class GeminiDataParser:
    def __init__(self, api_key: str, model_name: str, logger: logging.Logger):
        if not api_key: raise ValueError("Google API key is required.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.logger = logger
        self.logger.info(f"GeminiDataParser initialized with model '{model_name}'.")

    def parse_text_to_model(self, raw_text: str, source_file: str) -> BillOfQuantities | None:
        thread_name = threading.current_thread().name
        self.logger.info(f"[{thread_name}] Starting Gemini parsing for {source_file}")
        schema = BillOfQuantities.model_json_schema()
        prompt = f"""
        You are a highly precise data extraction tool. Your only purpose is to convert unstructured text into a specific JSON format based on the provided schema. Do not invent new keys or structures.

        **CRITICAL INSTRUCTIONS:**
        1.  **Follow the Schema:** The final JSON object MUST validate against the provided JSON schema.
        2.  **Hierarchical Extraction:** For main items referencing a "Sheet No.X", find the corresponding sub-table and populate the `components` field.
        3.  **No Extra Keys:** Do not add keys like "document_title" or "subsections". Only use the keys specified in the schema (`title`, `item_code`, `items`, `summary`).

        ---
        **EXAMPLE OF HOW TO PROCESS TEXT:**

        ### Example Input Text:
        ```        Item Code No. 0101
        Cost data for 33/11 KV, 1x5 MVA Substation
        Sr.No. Description Unit Qty. Rate/Unit Rs. Total Cost Rs.
        1 33 KV Lightning Arrestors Set 2 13571.00 27142.00
        2 Gantry Structure as per Sheet No.1 Nos 1 121541.00 121541.00
        ...
        Sheet No.1
        Cost data for 33 KV Gantry
        Sr.No. Description of Material Unit Qty. RT/U Rs. Amt.Rs.
        1 Column type HG MT 1.984 48500.00 96224.00
        ```

        ### Corresponding Correct JSON Output:
        ```json
        {{
          "title": "Cost data for 33/11 KV, 1x5 MVA Substation", "item_code": "0101",
          "items": [
            {{"serial_number": 1, "description": "33 KV Lightning Arrestors", "unit": "Set", "quantity": 2, "rate_per_unit": 13571.00, "total_cost": 27142.00, "components": null}},
            {{"serial_number": 2, "description": "Gantry Structure as per Sheet No.1", "unit": "Nos", "quantity": 1, "rate_per_unit": 121541.00, "total_cost": 121541.00,
              "components": [{{"description": "Column type HG", "unit": "MT", "quantity": 1.984, "rate_per_unit": 48500.00, "total_cost": 96224.00}}]
            }}
          ], "summary": {{}}
        }}
        ```
        ---

        **Now, apply these rules to the following text.**

        **JSON Schema to strictly follow:**
        ```json
        {json.dumps(schema, indent=2)}
        ```

        **Full Text Content to Parse:**
        ---
        {raw_text}
        ---

        Your response must be ONLY the valid JSON object.
        """
        try:
            generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
            response = self.model.generate_content(prompt, generation_config=generation_config)
            validated_model = BillOfQuantities.model_validate_json(response.text)
            self.logger.info(f"[{thread_name}] Gemini parsing and validation successful for {source_file}!")
            return validated_model
        except ValidationError as e:
            self.logger.error(f"[{thread_name}] Pydantic validation failed for {source_file}: {e}")
            self.logger.error(f"[{thread_name}] Gemini raw response that failed validation for {source_file}:\n{response.text}")
            return None
        except Exception as e:
            self.logger.error(f"[{thread_name}] Gemini parsing failed for {source_file}: {e}", exc_info=False)
            return None

# ==============================================================================
#  5. WORKER FUNCTION FOR MULTITHREADING
# ==============================================================================
def process_document_pipeline(file_path: str, ocr_processor: MistralOCRProcessor, parser: GeminiDataParser, output_dir: str):
    try:
        ocr_result = ocr_processor.process_document(file_path)
        if not ocr_result or not ocr_result.full_text:
            return (file_path, "OCR_FAILED", "No text extracted or OCR error.")
        source_filename = os.path.basename(file_path)
        structured_model = parser.parse_text_to_model(ocr_result.full_text, source_filename)
        if not structured_model:
            return (file_path, "PARSING_FAILED", "Gemini failed to parse or validate the data.")
        base_name = os.path.splitext(source_filename)[0]
        output_filename = os.path.join(output_dir, f"{base_name}_structured.json")
        with open(output_filename, "w") as f:
            f.write(structured_model.model_dump_json(indent=4))
        return (file_path, "SUCCESS", output_filename)
    except Exception as e:
        return (file_path, "UNHANDLED_EXCEPTION", str(e))

# ==============================================================================
#  6. MAIN METHOD
# ==============================================================================
if __name__ == "__main__":
    start_time = time.time()
    
    # --- SETUP ---
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(Config.LOG_FILE_PATH, 'w'), logging.StreamHandler()])
    main_logger = logging.getLogger("Main")

    mistral_api_key = os.environ.get("MISTRAL_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not mistral_api_key or not google_api_key:
        main_logger.critical("FATAL: MISTRAL_API_KEY or GOOGLE_API_KEY not found in .env file.")
    else:
        os.makedirs(Config.OUTPUT_DIRECTORY, exist_ok=True)
        documents_to_process = [os.path.join(Config.SOURCE_DIRECTORY, f) for f in os.listdir(Config.SOURCE_DIRECTORY) if f.lower().endswith('.pdf')]
        
        if not documents_to_process:
            main_logger.warning(f"No PDF files found in the directory: {Config.SOURCE_DIRECTORY}")
        else:
            main_logger.info(f"Found {len(documents_to_process)} documents to process with up to {Config.MAX_WORKERS} parallel threads.")
            
            # Initialize processors ONCE and pass them to the threads
            ocr_processor = MistralOCRProcessor(api_key=mistral_api_key, model_name=Config.MISTRAL_OCR_MODEL, logger=logging.getLogger("MistralOCRProcessor"))
            gemini_parser = GeminiDataParser(api_key=google_api_key, model_name=Config.GEMINI_PARSER_MODEL, logger=logging.getLogger("GeminiDataParser"))
            
            success_count = 0; failure_count = 0

            # --- EXECUTION WITH THREAD POOL AND TQDM ---
            with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
                future_to_path = {executor.submit(process_document_pipeline, path, ocr_processor, gemini_parser, Config.OUTPUT_DIRECTORY): path for path in documents_to_process}
                for future in tqdm(concurrent.futures.as_completed(future_to_path), total=len(documents_to_process), desc="Processing Documents"):
                    path = future_to_path[future]
                    try:
                        filepath, status, message = future.result()
                        if status == "SUCCESS": success_count += 1
                        else: failure_count += 1; main_logger.error(f"Failed to process {os.path.basename(filepath)}. Status: {status}. Reason: {message}")
                    except Exception as exc: failure_count += 1; main_logger.error(f"{os.path.basename(path)} generated an exception: {exc}")
            
            # --- FINAL SUMMARY ---
            total_time = time.time() - start_time
            summary = (
                f"\n{'='*50}\n"
                f"{'PROCESS COMPLETE':^50}\n"
                f"{'='*50}\n"
                f"Total documents processed: {len(documents_to_process)}\n"
                f"  - Successful: {success_count}\n"
                f"  - Failed:     {failure_count}\n"
                f"Total execution time: {total_time:.2f} seconds\n"
            )
            if failure_count > 0:
                summary += f"\nCheck '{Config.LOG_FILE_PATH}' for details on failed documents.\n"
            summary += "="*50
            print(summary)
            