import pytesseract
from PIL import Image
from typing import Optional


class OCRProcessor:
    def __init__(self, lang: str = 'eng+chi_tra+chi_sim'):
        self.lang = lang
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError("Tesseract OCR not found. Please install Tesseract OCR.")
    
    def extract_text(self, image_path: str, lang: Optional[str] = None) -> str:
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(
                image, 
                lang=lang or self.lang,
                config='--oem 3 --psm 6'
            )
            return text.strip()
        except Exception as e:
            return f"OCR Error: {str(e)}"
    
    def extract_text_with_confidence(self, image_path: str, lang: Optional[str] = None) -> tuple[str, float]:
        try:
            image = Image.open(image_path)
            data = pytesseract.image_to_data(
                image,
                lang=lang or self.lang,
                config='--oem 3 --psm 6',
                output_type=pytesseract.Output.DICT
            )
            
            text_parts = []
            confidences = []
            
            for i, word in enumerate(data['text']):
                if word.strip():
                    text_parts.append(word)
                    confidences.append(data['conf'][i])
            
            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return text, avg_confidence
        except Exception as e:
            return f"OCR Error: {str(e)}", 0.0
    
    def is_text_detected(self, image_path: str, threshold: float = 30.0) -> bool:
        _, confidence = self.extract_text_with_confidence(image_path)
        return confidence > threshold