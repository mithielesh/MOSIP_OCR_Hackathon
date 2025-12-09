from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
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
        
        # 1. Vision Model: TrOCR Printed
        # CHANGED: Switched to 'printed' model for high accuracy on forms.
        # Note: Change to 'trocr-base-handwritten' when you add the handwriting feature later.
        print("Loading TrOCR Printed model...")
        self.processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
        self.model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
        
        # 2. Detection Model: EasyOCR
        # Used for finding where the text is.
        self.detector = easyocr.Reader(['en'], gpu=False) # Set gpu=True if you have CUDA
        
        print("System Ready.")

    def preprocess_image(self, image_path):
        """
        Enhanced preprocessing pipeline for printed forms.
        """
        img = cv2.imread(image_path)
        
        # Denoise to remove scan artifacts
        dst = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        gray = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
        
        # Otsu's thresholding automatically finds the best separation for printed text
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary, Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    def trocr_read(self, image_crop):
        """
        Performs OCR on a specific image crop.
        """
        try:
            # excessive padding can confuse the model, ensuring crop is clean
            pixel_values = self.processor(images=image_crop, return_tensors="pt").pixel_values
            generated_ids = self.model.generate(pixel_values)
            text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return text.strip()
        except Exception as e:
            return ""

    def group_text_into_lines(self, boxes, original_image):
        """
        Crucial for Forms: Groups detected boxes into visual lines.
        This prevents 'Name' and 'Age' from getting mixed up.
        """
        # 1. Sort all boxes primarily by Top-Y
        boxes.sort(key=lambda x: x[0][0][1])
        
        lines = []
        current_line = []
        # Threshold: if vertical difference is < 20px, consider it the same line
        y_threshold = 20 

        for box in boxes:
            if not current_line:
                current_line.append(box)
                continue
            
            # Compare Y of current box with the average Y of the current line
            avg_y = sum([b[0][0][1] for b in current_line]) / len(current_line)
            box_y = box[0][0][1]

            if abs(box_y - avg_y) < y_threshold:
                current_line.append(box)
            else:
                lines.append(current_line)
                current_line = [box]
        
        if current_line:
            lines.append(current_line)

        # 2. Sort each line by Left-X to read Left-to-Right
        final_text_lines = []
        for line in lines:
            line.sort(key=lambda x: x[0][0][0])
            
            line_text = []
            for bbox, _, _ in line:
                # Crop and Read
                tl, tr, br, bl = bbox
                
                # Dynamic padding based on box size
                h = int(max(bl[1], br[1])) - int(min(tl[1], tr[1]))
                pad = int(h * 0.1) # 10% padding
                
                x_min = max(0, int(min(tl[0], bl[0])) - pad)
                x_max = min(original_image.width, int(max(tr[0], br[0])) + pad)
                y_min = max(0, int(min(tl[1], tr[1])) - pad)
                y_max = min(original_image.height, int(max(bl[1], br[1])) + pad)

                crop = original_image.crop((x_min, y_min, x_max, y_max))
                text = self.trocr_read(crop)
                if text:
                    line_text.append(text)
            
            if line_text:
                # Join words in the line with space
                final_text_lines.append(" ".join(line_text))
                
        return final_text_lines

    def clean_with_ai(self, structured_text_lines):
        """
        Uses Phi-3 to parse the structured lines into JSON.
        """
        print("Processing semantic structure via Phi-3...")
        
        # Join lines with newlines
        context_text = "\n".join(structured_text_lines)

        # STRICT PROMPT: Forces the LLM to act as a pure data extraction engine
        prompt = f"""
        You are a strictly compliant JSON data extractor.
        
        INPUT TEXT:
        \"\"\"
        {context_text}
        \"\"\"
        
        TASK:
        1. Extract the following fields: Name, Age, Gender, Address, Email, Phone.
        2. FIXES: 
           - If 'Age' is '1', 'I', or '|', it is a border error. Look for a 2-digit number (e.g., 29) or set to null.
           - Ensure Email is lowercase.
        3. OUTPUT: Return ONLY valid JSON. Do not write any introduction or explanation.
        
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
            # Check if Ollama is actually reachable
            response = ollama.chat(model='phi3', messages=[{'role': 'user', 'content': prompt}])
            content = response['message']['content']
            
            # Find the JSON object within the response
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                print("LLM Error: Output was not JSON. content:", content)
                # Fallback: Attempt to manually map simple fields if AI fails
                return self.manual_fallback(structured_text_lines)
                
        except Exception as e:
            print(f"CRITICAL LLM FAILURE: {e}")
            print("Make sure 'ollama serve' is running!")
            return self.manual_fallback(structured_text_lines)

    def manual_fallback(self, lines):
        """
        A simple backup parser if the AI is offline, so you don't get a giant text blob.
        """
        data = {}
        text_blob = " ".join(lines)
        
        # Simple Regex heuristics
        data["Email"] = re.search(r'[\w\.-]+@[\w\.-]+', text_blob).group(0) if re.search(r'[\w\.-]+@[\w\.-]+', text_blob) else ""
        data["Phone"] = re.search(r'\+?\d[\d -]{8,}', text_blob).group(0) if re.search(r'\+?\d[\d -]{8,}', text_blob) else ""
        data["Name"] = "Extraction Failed (Check Ollama)"
        
        return data

    def extract_data(self, image_path):
        if not os.path.exists(image_path):
            return {"error": "File not found"}

        print(f"Processing Document: {image_path}")

        # 1. Detection & Preprocessing
        detection_img_np, original_pil = self.preprocess_image(image_path)
        
        # EasyOCR for Bounding Boxes
        # We use a lower threshold to catch faint text on forms
        boxes = self.detector.readtext(detection_img_np, mag_ratio=2, text_threshold=0.4)
        
        if not boxes:
            return {"error": "No text detected"}

        # 2. Smart Grouping & Recognition
        # This replaces the simple sort and flat list
        structured_lines = self.group_text_into_lines(boxes, original_pil)
        
        print(f"Extracted {len(structured_lines)} lines of text.")
        # Debug: print lines to see if structure is preserved
        # for l in structured_lines: print(l)

        # 3. Structural Parsing
        final_data = self.clean_with_ai(structured_lines)
        

        return final_data