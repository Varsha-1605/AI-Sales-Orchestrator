"""Text translation with googletrans."""

from typing import Any, Dict

from loguru import logger


async def translate(text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
    try:
        from googletrans import Translator
        translator = Translator()

        translation = await translator.translate(
            text,
            src=source_lang,
            dest=target_lang
        )

        return {
            "success": True,
            "translated_text": translation.text,
            "detected_lang": translation.src,
            "target_lang": target_lang
        }

    except ImportError:
        return {
            "success": False,
            "translated_text": text,
            "error": "Translation library not installed. Install googletrans>=4.0.2"
        }
    except Exception as e:
        logger.error("Translation error: {}", e)
        return {
            "success": False,
            "translated_text": text,
            "error": str(e)
        }
