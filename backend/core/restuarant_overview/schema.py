from typing import Dict
from pydantic import BaseModel, Field

class MenusOverviewSummary(BaseModel):
    summary: str = Field(
        description=(
            "A single concise paragraph summarizing the most popular menu items based on review volume. "
            "Should group items by how they are typically ordered (e.g., main individual dishes, shared dishes, "
            "sides or add-ons) rather than describing each dish in detail. "
            "Written for a US audience unfamiliar with the cuisine, assuming each menu item has its own detail page."
        )
    )

    glossary: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "A dictionary of short, curiosity-oriented explanations of common romanized menu terms that appear repeatedly. "
            "Keys should be the romanized term (e.g., 'Maeun') and values should be a simple grounding definition "
            "(e.g., 'spicy'), without non-English characters, long descriptions, or subjective language."
        )
    )
