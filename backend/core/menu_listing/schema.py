from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field


class MenuOption(BaseModel):
    size: List[str] = Field(
        default_factory=list,
        description=(
            "Available size options specifically listed for this item or for the parent category or overarching section "
            "it belongs to (e.g., Small, Medium, Large). Return an empty list if no sizes are specified."
        ),
        example=["Small", "Medium", "Large"]
    )

    spiciness: List[str] = Field(
        default_factory=list,
        description=(
            "Spiciness levels that are explicitly offered as customer-selectable options for this menu item, or inherited from its parent category or section"
            "(e.g., Mild, Medium, Spicy, or numeric scales such as 1-5)."
            "Include only spiciness levels presented as choices the customer can select. Do not infer spiciness from dish descriptions. "
            "Return an empty list if not specified."
        ),
        example=["Mild", "Medium", "Spicy"]
    )

    toppings: List[str] = Field(
        default_factory=list,
        description=(
            "Optional toppings or add-ons specifically listed for this item or for the parent category or overarching section "
            "it belongs to. Return an empty list if no specific toppings are shown."
        ),
        example=["Extra noodles", "Add egg"]
    )

    proteins: List[str] = Field(
        default_factory=list,
        description=(
            "Protein options that are explicitly offered as customer-selectable choices for this menu item,"
            "or inherited from its parent category or section (e.g., Chicken, Beef, Pork, Tofu, Shrimp)."
            "Include only proteins presented as alternatives the customer can choose from."
            "Do not include the default or inherent protein of the dish."
            "Return an empty list if no selectable protein options are listed."
        ),
        example=["Chicken", "Beef", "Pork", "Tofu", "Shrimp"]
    )

    other_option: List[str] = Field(
        default_factory=list,
        description=(
            "Any other customization options or choices specifically listed for this item or for the parent category "
            "or overarching section it belongs to that do not fit into size, spiciness, toppings, or proteins. "
            "Return an empty list if no other options are listed."
        ),
        example=["Brown Rice", "White Rice"]
    )


class DietaryIngredients(BaseModel):
    fish: List[str] = Field(
        default_factory=list,
        description="List of specific ingredients containing fish, among salmon, tuna, cod, etc. Return an empty list if none are explicitly mentioned.",
        example=["salmon", "fish sauce"]
    )   
    shellfish: List[str] = Field(
        default_factory=list,
        description="List of specific ingredients containing shellfish, among shrimp, crab, lobster, clam, etc. Return an empty list if none are explicitly mentioned.",
        example=["shrimp", "clam"]
    )
    red_meat: List[str] = Field(
        default_factory=list,
        description=(
            "List of red meat types explicitly mentioned on the menu, using generic ingredient terms only (e.g., beef, pork, lamb)."
            "Do not include cuts, preparations, compound phrases, or dish-specific terms (e.g., “beef brisket”, “oxtail”, “braised pork”)."
            "Return an empty list if no red meat is explicitly mentioned."
        ),
        example=["pork"]
    )
    poultry: List[str] = Field(
        default_factory=list,
        description="List of specific ingredients containing poultry, among chicken, duck, turkey, etc. Return an empty list if none are explicitly mentioned.",
        example=["turkey"]
    )
    allergen_ingredients: List[str] = Field(
        default_factory=list,
        description="List of specific ingredients containing allergens, among peanuts, soy, wheat, egg, sesame seeds etc. Return an empty list if none are explicitly mentioned.",
        example=["peanuts"]
    )


class MenuItem(BaseModel):
    name: str = Field(
        description=(
            "The primary dish name written in English letters only. "
            "If the menu shows both English and non-English names, use the English name."
            "If the menu shows only a non-English name, provide a standard English romanization. "
            "Put extra effort into OCR to ensure the name is read exactly as written on the menu. "
            "Do NOT output non-English scripts."
            ),
        example="Tom Yum Goong"
    ) 

    nicknames: List[str] = Field(
        default_factory=list,
        description=(
            "Two or three alternative English names that English-speaking customers are likely to type in reviews when referring to this dish. "
            "Base these names primarily on the menu-board description and visible text. "
            "When multiple ingredients or features are listed, focus on the element that defines the dish’s identity, "
            "rather than secondary or garnish ingredients."
            "Use general culinary knowledge only to identify this defining element, not to introduce new concepts or ingredients."
            "Must use English letters only, be meaningfully different from the primary name (not simple spacing, punctuation, or minor spelling variants), and be concise (fewer than 4 words). "
            "Leave this list empty only if English-speaking customers would almost always type the primary name exactly as-is when writing reviews."
            "Example: if the menu name is “Tom Yum Goong” and the description mentions shrimp, lemongrass, lime, chili, and mushrooms,"
            "an acceptable alternative is “Spicy Shrimp Soup,” NOT “Lemongrass Mushroom Soup” because shrimp defines the dish rather than the herbs or broth."
        ),
        example=["Spicy Shrimp Soup", "Tom Yum Soup"]
    )

    price: float = Field(
        default=-1.0,
        description=(
            "The numerical price in USD. If multiple prices exist for different sizes, "
            "extract the price for the standard/medium option. Return -1.0 if the price is missing or illegible."
        ),
        example=14.99
    )  

    options: MenuOption = Field(
        default_factory=MenuOption,
        description=(
            "Structured customization options such as size, spiciness, toppings, protein choices, "
            "and other miscellaneous options."
        )
    )

    description: str = Field(
        default="",
        description=(
            "An exact textual description or list of ingredients as printed on the menu. "
            "Extracted verbatim from OCR. Return an empty string if no description is provided."
        ),
        example="Spicy noodle soup with various seafood and vegetables."
    )

    ingredients_by_category: DietaryIngredients = Field(
        default_factory=DietaryIngredients,
        description="Categorized list of ingredients based on fixed allergen and protein source categories (fish, peanuts, soy, seafood, red meat, poultry, egg). Do NOT infer ingredients that are not explicitly stated on the menu board."
    )

    dietary_labels: List[str] = Field(
        default_factory=list,
        description=(
            "Specific dietary restriction labels explicitly mentioned for the item. "
            "Choose only from: gluten-free, dairy-free, nut-free, egg-free, vegan, vegetarian, halal, kosher. "
            "ONLY include a label if it is explicitly stated on the menu board."
            "Also include a label if the menu explicitly mentions that a dietary restriction option is available, "
            "even if it is not the default (e.g., 'vegan available upon request', 'gluten-free bread option')."
            "As an exception, if 'Impossible™' is explicitly mentioned as substitution, include 'vegan' in this list. "
            "Sometimes, the label is represented as a symbol with appropriate legend (e.g., a crossed-out wheat symbol for gluten-free). Do NOT infer labels from the ingredients_by_category field."
        ),
        example=["gluten-free", "nut-free"]
    )


class MenuExtractionResponse(BaseModel):
    items: List[MenuItem]
