# backend/verifier.py
from difflib import SequenceMatcher

class Verifier:
    def __init__(self):
        pass

    def calculate_similarity(self, extracted_text, user_input):
        """
        Calculates a confidence score (0-100) between OCR text and User Input.
        Uses SequenceMatcher (similar to Levenshtein distance).
        """
        if not extracted_text or not user_input:
            return 0.0

        # Normalize: Convert to lowercase and strip spaces for fair comparison
        clean_extracted = str(extracted_text).lower().strip()
        clean_input = str(user_input).lower().strip()

        # Calculate similarity ratio (0.0 to 1.0)
        similarity = SequenceMatcher(None, clean_extracted, clean_input).ratio()
        
        # Convert to percentage
        score = round(similarity * 100, 2)
        
        return score

    def verify_field(self, field_name, extracted_value, user_value):
        """
        Compares a specific field and returns a detailed status.
        """
        score = self.calculate_similarity(extracted_value, user_value)
        
        status = "MISMATCH"
        if score == 100:
            status = "MATCH"
        elif score > 80:
            status = "PARTIAL_MATCH" # Likely a typo or OCR error (e.g., '0' vs 'O')
            
        return {
            "field": field_name,
            "extracted": extracted_value,
            "user_input": user_value,
            "score": score,
            "status": status
        }