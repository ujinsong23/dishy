from __future__ import annotations
from typing import List, Literal, Dict, Optional
from pydantic import BaseModel, Field

from menu_listing.schema import DietaryIngredients
from text_review_labeling.constants import DIETARY_OPTIONS_ALL


class DietaryClaim(BaseModel):
    is_adherent: bool = Field(
        description="True if the review suggests the dish is safe "
            "or can be modified to be safe upon request(adherent to the dietary option). "
            "False if a review discusses the dietary option and explicitly warns that the dish is NOT safe or contains violations."
    )
    evidences: List[DietaryClaimEvidence]


class DietaryClaimEvidence(BaseModel):
    review_id: int = Field(
        description="ID of the review that provides evidence for the dietary claim."
    )
    quote: str = Field(
        description="Exact minimal quote from the review regarding the dietary option. Do NOT paraphrase."
    )


# -------------------------
# Menu vs review diff flags
# -------------------------

class ReviewDiffNotes(BaseModel):
    note: str = Field(
        description=(
            "Short objective notes describing discrepancies between reviews and the menu. "
            "Common discrepancies may include availability, unlisted price changes, specials, flavor, portion sizes, or secret menu options."
      ),
        example="The menu shows a regular burger, but reviews describe a \"secret\" spicy sauce upon request. Reviews mention it is frequently sold out."
    )
    evidence_review_ids: List[int] = Field(
        default_factory=list,
        description="List of review IDs that support this note."
    )

# -------------------------
# Final aggregated review summary per menu item
# -------------------------

class MenuReviewSummary(BaseModel):

    relevant_review_ids: List[int] = Field(
        default_factory=list,
        description="IDs of reviews that were determined to clearly discuss this menu item and used as evidence."
    )

    objective_summary: str = Field(
        description=(
            "Concise, neutral explanation of what this dish is at this specific restaurant, "
            "written for someone unfamiliar with the cuisine. "
            "Describe the dish’s composition and preparation style as inferred from reviews, "
            "not subjective taste or general culinary knowledge."
        ),
        example="Spicy and sour prawn soup with mushrooms, galangal, and lemongrass. Notes of lime juice and chili paste."
    )

    appearance: str = Field(
        default="",
        description=(
            "A single-sentence, comprehensive visual description of the main dish used for image matching. "
            "Include only clearly visible ingredients with their placement and the container’s type, material, color, and shape. "
            "Emphasize visual traits that distinguish this dish from SIBLING_MENU_ITEMS. "
            "Strictly exclude all side items. "
            "Begin with a natural dish identity phrase (e.g., 'Fried pork with...', 'Noodle soup featuring...')"
        ),
        example="Red soup of spicy prawn and lemongrass with straw mushrooms floating on surface and cilantro garnish on top. Served in a silver metal hot pot"
    )

    ingredients_by_category: DietaryIngredients = Field(
        default_factory=DietaryIngredients,
        description="Ingredients mentioned in reviews, categorized by protein/allergen source."
    )

    dietary_claims: Dict[str, Optional[DietaryClaim]] = Field(
        default_factory=dict,
        description="Dietary-related claims mentioned in reviews. Keys must be one of: vegan, gluten-free, dairy-free, nut-free, egg-free, vegetarian, halal, kosher. Values are null if not mentioned."
    )

    diff_notes: List[ReviewDiffNotes] = Field(
        default_factory=list,
        description="Notes regarding discrepancies between the restaurant menu and customer reviews(excluding dietary restrictions or ingredient-related differences)."
    )
