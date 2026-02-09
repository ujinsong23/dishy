import os
import base64
import time
from google import genai
from google.genai import types

from utils.helpers import get_curr_time
from image_generating.constants import (
    API_KEY, 
    NANOBANANA_MODEL_NAME, 
    PROMPT_TEMPLATE
)

def prepare_prompt(menu_metadata: dict) -> str:
    ingredients_list = []
    for lst in menu_metadata['from_reviews']['ingredients_by_category'].values():
        ingredients_list.extend(lst)
    ingredients_list = ', '.join(ingredients_list)

    return PROMPT_TEMPLATE.format(
        name = menu_metadata['from_menuboard']['name'],
        description = menu_metadata['from_menuboard']['description'],
        appearance = menu_metadata['from_reviews']['appearance'],
        ingredients_list = ingredients_list,
    )

def image2base64(image_path: str) -> str:
    """Converts an image file to a base64 string."""
    with open(image_path, "rb") as img_file:
        b64_bytes = base64.b64encode(img_file.read())
        mime_type = "image/" + os.path.splitext(image_path)[1][1:]  # e.g., 'jpeg', 'png'
        return f"data:{mime_type};base64,{b64_bytes.decode('utf-8')}"

def call_nanobanana(
    image_path: str,
    prompt: str,
) -> str:
    """
    Generates an edited image using Gemini.
    Equivalent to generateImageEdit in geminiService.ts.
    
    Args:
        image_path: Path to the image file
        prompt: Text prompt for editing
        
    Returns:
        Base64 string of the resulting image
    """
    client = genai.Client(vertexai=True, location="global")

    image_bytes_b64 = image2base64(image_path)
    mime_type, base64_data = image_bytes_b64.split(';base64,')
    mime_type = mime_type.split(':')[1]  # e.g., 'image/jpeg

    # Decode base64 to bytes once
    try:
        image_bytes = base64.b64decode(base64_data)
    except Exception as e:
         raise RuntimeError(f"Failed to decode image: {e}")

    max_retries = 5
    base_delay = 30

    for attempt in range(max_retries + 1):
        try:
            # Construct the request
            response = client.models.generate_content(
                model=NANOBANANA_MODEL_NAME,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=mime_type
                            ),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio="1:1",
                        image_size="1K",
                    )
                )
            )

            candidate = response.candidates[0] if response.candidates else None
            if not candidate:
                raise RuntimeError("No candidates returned from API")

            for part in candidate.content.parts:
                if part.inline_data:
                    return part.inline_data.data
            return None

        except Exception as error:
            status_code = getattr(error, 'code', None) or getattr(error, 'status_code', None)
            error_msg = str(error)
            
            if status_code == 429 or "429" in error_msg:
                if attempt < max_retries:
                    sleep_time = base_delay + attempt*5 
                    print(f"[{get_curr_time()}]Rate limit (429) hit. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    continue
            
            if "Requested entity was not found" in error_msg:
                raise RuntimeError("API_KEY_EXPIRED")
                
            raise RuntimeError(error_msg if error_msg else "Failed to generate image edit.")
