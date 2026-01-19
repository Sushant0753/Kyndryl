import pytesseract
from PIL import Image
from typing import Optional, Dict, Any
import io
from configs.config import DocumentSettings
from lib.logger import logger


class OCRService:
    """Service for OCR text extraction from images using PyTesseract"""

    def __init__(self):
        self.settings = DocumentSettings()

        try:
            # Test if Tesseract is available
            pytesseract.get_tesseract_version()
            self.enabled = True
            logger.info(f"OCR Service initialized with languages: {self.settings.OCR_LANGUAGES}")
        except Exception as e:
            logger.error(f"Tesseract not found or not properly configured: {e}")
            self.enabled = False

    def extract_text_from_image(self, image_content: bytes) -> str:
        """
        Extract text from image using PyTesseract OCR

        Args:
            image_content: Raw image bytes

        Returns:
            str: Extracted text, empty string if failed
        """
        if not self.enabled:
            logger.warning("OCR is disabled - Tesseract not properly configured")
            return ""

        if not image_content:
            logger.warning("Empty image content provided for OCR")
            return ""

        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_content))

            # Convert to RGB if necessary (handles transparency, etc.)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')

            logger.info(f"Processing image for OCR: {image.size[0]}x{image.size[1]} pixels, mode: {image.mode}")

            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)

            # Configure Tesseract
            custom_config = self._get_tesseract_config()

            # Extract text using Tesseract
            extracted_text = pytesseract.image_to_string(
                processed_image,
                lang=self.settings.OCR_LANGUAGES,
                config=custom_config
            )

            # Clean up the extracted text
            cleaned_text = self._clean_extracted_text(extracted_text)

            logger.info(f"OCR extraction successful: {len(cleaned_text)} characters extracted")

            return cleaned_text

        except Exception as e:
            logger.error(f"OCR text extraction failed: {e}", exc_info=True)
            return ""

    def extract_text_with_confidence(self, image_content: bytes) -> Dict[str, Any]:
        """
        Extract text with confidence scores and additional metadata

        Args:
            image_content: Raw image bytes

        Returns:
            dict: Contains 'text', 'confidence', 'word_count', etc.
        """
        if not self.enabled:
            return {"text": "", "confidence": 0, "word_count": 0, "error": "OCR disabled"}

        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_content))

            # Convert to RGB if necessary
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')

            # Preprocess image
            processed_image = self._preprocess_image(image)

            # Configure Tesseract
            custom_config = self._get_tesseract_config()

            # Extract text with confidence data
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.settings.OCR_LANGUAGES,
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )

            # Extract text
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.settings.OCR_LANGUAGES,
                config=custom_config
            )

            # Clean text
            cleaned_text = self._clean_extracted_text(text)

            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Count words
            word_count = len([word for word in data['text'] if word.strip()])

            result = {
                "text": cleaned_text,
                "confidence": round(avg_confidence, 2),
                "word_count": word_count,
                "image_size": image.size,
                "languages_used": self.settings.OCR_LANGUAGES
            }

            logger.info(f"OCR with confidence: {len(cleaned_text)} chars, {avg_confidence:.2f}% confidence, {word_count} words")

            return result

        except Exception as e:
            logger.error(f"OCR extraction with confidence failed: {e}", exc_info=True)
            return {"text": "", "confidence": 0, "word_count": 0, "error": str(e)}

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results

        Args:
            image: PIL Image object

        Returns:
            PIL Image object: Preprocessed image
        """
        try:
            # Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')

            # Resize if image is too small (improves OCR accuracy)
            min_size = 300
            if image.size[0] < min_size or image.size[1] < min_size:
                ratio = max(min_size / image.size[0], min_size / image.size[1])
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.debug(f"Image resized to {new_size} for better OCR")

            return image

        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {e}")
            return image

    def _get_tesseract_config(self) -> str:
        """
        Get Tesseract configuration string for optimal OCR

        Returns:
            str: Tesseract config string
        """
        # PSM 6: Uniform block of text
        # OEM 3: Default, based on what is available
        config = r'--oem 3 --psm 6'

        # Additional configs for better accuracy
        config += r' -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz '
        config += r'-c preserve_interword_spaces=1'

        return config

    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text

        Args:
            text: Raw extracted text

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace and normalize line breaks
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)

        # Remove excessive spacing
        import re
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)

        return cleaned_text.strip()

    def get_supported_languages(self) -> list:
        """
        Get list of supported languages

        Returns:
            list: Available language codes
        """
        if not self.enabled:
            return []

        try:
            langs = pytesseract.get_languages(config='')
            logger.info(f"Available OCR languages: {langs}")
            return langs
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return []

    def is_available(self) -> bool:
        """
        Check if OCR service is available

        Returns:
            bool: True if Tesseract is properly configured
        """
        return self.enabled