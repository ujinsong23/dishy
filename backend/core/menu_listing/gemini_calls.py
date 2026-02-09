from typing import List, Dict, Any, Tuple
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google import genai
from google.genai import types
from menu_listing.constants import MAX_SIDE
from PIL import Image
import io
from utils.helpers import get_curr_time

from menu_listing.constants import (
    GCP_PROJECT_ID, 
    GEMINI_MODEL
)
from menu_listing.schema import MenuExtractionResponse

def _call_gemini_v2(image_data: List[bytes], prompt_text: str, image_dates: List[str]) -> List[Dict[str, Any]]:
    """Inference using vertexai SDK (Gemini 2.5)."""
    
    parts = [prompt_text]
    for idx, (data, date) in enumerate(zip(image_data, image_dates)):
        parts.append(f"Image {idx+1} from {date}")
        parts.append(Part.from_data(data=data, mime_type="image/jpeg"))

    model = GenerativeModel(GEMINI_MODEL)
    print(f"[{get_curr_time()}] Running {GEMINI_MODEL} for menu extraction...")
    response = model.generate_content(
        parts,
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=MenuExtractionResponse.model_json_schema()
        )
    )
    extraction = MenuExtractionResponse.model_validate_json(response.text)
    return [item.model_dump() for item in extraction.items]


def _call_gemini_v3(
    image_data: List[bytes],
    prompt_text: str,
    image_dates: List[str],
) -> List[Dict[str, Any]]:
    """Inference using Gemini 3 Flash (google.genai SDK)."""

    client = genai.Client(vertexai=True, location="global", project=GCP_PROJECT_ID)

    parts: List[types.Part] = [
        types.Part.from_text(text=prompt_text)
    ]

    for idx, (data, date) in enumerate(zip(image_data, image_dates)):
        parts.append(
            types.Part.from_text(text=f"Image {idx+1} from {date}")
        )
        parts.append(
            types.Part.from_bytes(
                data=data,
                mime_type="image/jpeg",
            )
        )
    
    print(f"[{get_curr_time()}] Running {GEMINI_MODEL} for menu extraction...")
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=parts,
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MenuExtractionResponse.model_json_schema(),
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        ),
    )

    json_text = response.candidates[0].content.parts[0].text
    # print_usage_metadata(response)

    extraction = MenuExtractionResponse.model_validate_json(json_text)
    return [item.model_dump() for item in extraction.items]


def print_usage_metadata(response):
    usage = response.usage_metadata
    if not usage:
        print("No usage metadata")
        return

    def _print_details(label, details):
        if not details:
            return
        print(f"{label}:")
        for d in details:
            print(f"  - {d.modality.value.lower():<6}: {d.token_count}")

    print("=== Gemini Usage Metadata ===")
    print(f"Prompt tokens        : {usage.prompt_token_count}")
    _print_details("  Prompt breakdown", usage.prompt_tokens_details)

    print(f"Cached content tokens: {usage.cached_content_token_count}")
    _print_details("  Cache breakdown", usage.cache_tokens_details)

    print(f"Output tokens        : {usage.candidates_token_count}")
    _print_details("  Output breakdown", usage.candidates_tokens_details)

    print(f"Thought tokens       : {usage.thoughts_token_count}")

    if usage.tool_use_prompt_token_count is not None:
        print(f"Tool prompt tokens   : {usage.tool_use_prompt_token_count}")
        _print_details("  Tool breakdown", usage.tool_use_prompt_tokens_details)

    print(f"Total tokens         : {usage.total_token_count}")
    print(f"Traffic type         : {usage.traffic_type.value}")
    print("============================")
