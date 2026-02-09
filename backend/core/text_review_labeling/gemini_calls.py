from typing import Dict, Any
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google import genai
from google.genai import types
from pydantic import BaseModel

from text_review_labeling.constants import (
    GCP_PROJECT_ID,
    SUMMARY_MODEL_GEMINI_2,
    SUMMARY_MODEL_GEMINI_3
)
from text_review_labeling.schema import MenuReviewSummary


def _call_gemini_v2(prompt: str) -> Dict[str, Any]:
    model = GenerativeModel(SUMMARY_MODEL_GEMINI_2)
    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=MenuReviewSummary.model_json_schema(),
            temperature=0
        )
    )
    extraction = MenuReviewSummary.model_validate_json(response.text)
    return extraction.model_dump()


def _call_gemini_v3(
    prompt: str,
    schema: BaseModel,
    model: str = None
) -> Dict[str, Any]:
    """Inference using Gemini 3 Flash (google.genai SDK)."""
    model = model or SUMMARY_MODEL_GEMINI_3

    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT_ID,
        location="global"
    )
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text=prompt)
                ],
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema.model_json_schema(),
            temperature=0,
            thinking_config=(
                types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW) if '3-pro' in model
                else types.ThinkingConfig(thinking_level="minimal")
            )
        ),
    )

    json_text = response.candidates[0].content.parts[0].text

    extraction = schema.model_validate_json(json_text)
    return extraction.model_dump()
