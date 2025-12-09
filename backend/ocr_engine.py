from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image, ImageOps
import easyocr
import os
import cv2
import numpy as np
import re
import ollama
import json

class OCREngine:
    def __init__(self):
        print("Initializing Intelligent Document Processing System...")
        
        # 1. Vision Model: TrOCR Printed (Default for English)
        print("Loading TrOCR Printed model...")
        self.processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
        self.model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
        
        # 2. Detection Model: EasyOCR (Supports English and Arabic)
        self.detector = easyocr.Reader(['en', 'ar'], gpu=False) 
        
        print("System Ready. Multi-lingual (Arabic) support active.")

    # --- Helper Functions ---

    def preprocess_image(self, image_path):
        """Enhanced preprocessing pipeline for printed forms."""
        img = cv2.imread(image_path)
        dst = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary, Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    def trocr_read(self, image_crop):
        """
        Performs OCR on a specific image crop (English only).
        Includes the border padding fix to prevent 'Age: 1' error.
        """
        try:
            # FIX: Add a white border to prevent reading box lines as '1' or 'I'.
            image_crop = ImageOps.expand(image_crop, border=10, fill="white")
            
            pixel_values = self.processor(images=image_crop, return_tensors="pt").pixel_values
            generated_ids = self.model.generate(pixel_values)
            text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            clean_text = text.strip()
            if clean_text in ["|", "]", "[", "1|", "|1", "I"]:
                return ""
            
            return clean_text
        except Exception as e:
            return ""

    def group_text_into_lines(self, boxes, original_image):
        """Groups detected boxes into visual lines for key-value association (English)."""
        boxes.sort(key=lambda x: x[0][0][1])
        lines, current_line, y_threshold = [], [], 20 

        for box in boxes:
            if not current_line:
                current_line.append(box)
                continue
            
            avg_y = sum([b[0][0][1] for b in current_line]) / len(current_line)
            box_y = box[0][0][1]

            if abs(box_y - avg_y) < y_threshold:
                current_line.append(box)
            else:
                lines.append(current_line)
                current_line = [box]
        
        if current_line:
            lines.append(current_line)

        final_text_lines = []
        for line in lines:
            line.sort(key=lambda x: x[0][0][0])
            line_text = []
            for bbox, _, _ in line:
                tl, tr, br, bl = bbox
                h = int(max(bl[1], br[1])) - int(min(tl[1], tr[1]))
                pad = int(h * 0.1) 
                x_min = max(0, int(min(tl[0], bl[0])) - pad)
                x_max = min(original_image.width, int(max(tr[0], br[0])) + pad)
                y_min = max(0, int(min(tl[1], tr[1])) - pad)
                y_max = min(original_image.height, int(max(bl[1], br[1])) + pad)

                crop = original_image.crop((x_min, y_min, x_max, y_max))
                text = self.trocr_read(crop)
                
                if text:
                    line_text.append(text)
            
            if line_text:
                final_text_lines.append(" ".join(line_text))
                
        return final_text_lines
        
    def manual_fallback(self, lines):
        """A simple backup parser if the AI is offline."""
        data = {}
        text_blob = " ".join(lines)
        data["Email"] = re.search(r'[\w\.-]+@[\w\.-]+', text_blob).group(0) if re.search(r'[\w\.-]+@[\w\.-]+', text_blob) else ""
        data["Phone"] = re.search(r'\+?\d[\d -]{8,}', text_blob).group(0) if re.search(r'\+?\d[\d -]{8,}', text_blob) else ""
        data["Name"] = "Extraction Failed (Check Ollama)"
        return data

    # --- Core Extraction and Parsing Methods ---

    def clean_with_ai(self, structured_text_lines, doc_type="printed"):
        """
        Uses Phi-3 to parse the structured lines into JSON, adapting to language/type.
        """
        print(f"Processing semantic structure via Phi-3 (Type: {doc_type})...")
        context_text = "\n".join(structured_text_lines)

        field_map = {
            "Name": "الاسم الكامل",
            "Age": "العمر",
            "Gender": "الجنس",
            "Address": "العنوان",
            "Email": "البريد الإلكتروني",
            "Phone": "رقم الهاتف"
        }
        
        if doc_type == "arabic":
            target_fields_str = f"English keys: {', '.join(field_map.keys())}. Arabic equivalents: {', '.join(field_map.values())}"
            prompt_instruction = (
                "The input text is in Arabic (Right-to-Left). Map the Arabic field names "
                "to the required English keys provided in the JSON SCHEMA."
            )
        else:
            target_fields_str = f"Extract the following English keys: {', '.join(field_map.keys())}"
            prompt_instruction = "The input is English printed text. Fix spelling/OCR errors."


        prompt = f"""
        You are a strictly compliant JSON data extractor.
        
        INPUT TEXT:
        \"\"\"
        {context_text}
        \"\"\"
        
        TASK:
        1. {prompt_instruction}
        2. {target_fields_str}.
        3. FIXES: If Age is '1', 'I', or '|', look for a 2-digit number (e.g., 29) or set to null.
        4. OUTPUT: Return ONLY valid JSON. Do not write any introduction or explanation.
        
        JSON SCHEMA:
        {{
            "Name": "string",
            "Age": "string",
            "Gender": "string",
            "Address": "string",
            "Email": "string",
            "Phone": "string"
        }}
        """

        try:
            response = ollama.chat(model='phi3', messages=[{'role': 'user', 'content': prompt}])
            content = response['message']['content']
            
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                print("LLM Error: Output was not JSON.")
                return self.manual_fallback(structured_text_lines)
                
        except Exception as e:
            print(f"CRITICAL LLM FAILURE: {e}")
            return self.manual_fallback(structured_text_lines)


    def extract_data(self, image_path, doc_type="printed"):
        if not os.path.exists(image_path):
            return {"error": "File not found"}

        print(f"Processing Document: {image_path} as {doc_type}")

        detection_img_np, original_pil = self.preprocess_image(image_path)
        
        if doc_type == "arabic":
            # Arabic Path: Use EasyOCR for both detection and recognition
            boxes_raw = self.detector.readtext(detection_img_np, detail=1, paragraph=True, allowlist='0123456789ءآأبتثجحخدذرزسشصضطظعغفقكلمنهويةىي') 
            structured_lines = [text for (bbox, text, conf) in boxes_raw]

        else: # English Printed Path: Use EasyOCR detection + TrOCR recognition
            boxes = self.detector.readtext(detection_img_np, mag_ratio=2, text_threshold=0.4)
            if not boxes:
                return {"error": "No text detected"}
            structured_lines = self.group_text_into_lines(boxes, original_pil)
        
        print(f"Extracted {len(structured_lines)} lines of text.")
        
        final_data = self.clean_with_ai(structured_lines, doc_type=doc_type)

        return final_data