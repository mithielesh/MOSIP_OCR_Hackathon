from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
from typing import Dict, Any

# Import your modules
from ocr_engine import OCREngine
from verifier import Verifier

app = FastAPI()

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Initializing Engines...")
ocr_engine = OCREngine()
verifier = Verifier()

# --- DATA MODELS ---

class SingleFieldRequest(BaseModel):
    field_name: str       
    extracted_text: str
    user_input: str

class FullFormVerificationRequest(BaseModel):
    extracted_data: Dict[str, Any]  # The JSON from OCR
    user_input_data: Dict[str, Any] # The JSON from the User form

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "MOSIP OCR API is Running!", "status": "Online"}

@app.post("/extract")
async def extract_text_api(
    file: UploadFile = File(...),
    doc_type: str = Form("printed") 
):
    """
    Step 1: Upload Image -> Get JSON Data
    """
    os.makedirs("uploads", exist_ok=True)
    temp_filename = f"uploads/{file.filename}"
    
    # Save the uploaded file temporarily
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Call the optimized Engine
    # Note: We are currently ignoring doc_type in the call because 
    # the engine is optimized for "Printed" forms right now.
    json_data = ocr_engine.extract_data(temp_filename)
    
    return {
        "filename": file.filename,
        "extracted_data": json_data, 
        "doc_type_detected": doc_type,
        "status": "success"
    }

@app.post("/verify")
async def verify_single_field(data: SingleFieldRequest):
    """
    Step 2a: Verify a single field (e.g., just the Name)
    """
    result = verifier.verify_field(
        data.field_name, 
        data.extracted_text, 
        data.user_input
    )
    return result

@app.post("/verify-full")
async def verify_full_form(data: FullFormVerificationRequest):
    """
    Step 2b: Verify the ENTIRE form in one click.
    Compares the OCR JSON against the User Input JSON.
    """
    verification_report = {}
    
    # Iterate through the user's input keys (Name, Age, etc.)
    for key, user_val in data.user_input_data.items():
        # Find corresponding key in OCR data (case-insensitive search is safer)
        extracted_val = data.extracted_data.get(key, "")
        
        # Verify this specific field
        verification_report[key] = verifier.verify_field(key, extracted_val, user_val)
        
    return {
        "overall_status": "completed",
        "field_results": verification_report
    }