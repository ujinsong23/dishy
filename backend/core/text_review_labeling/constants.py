import os
from dotenv import load_dotenv
from utils.path_utils import ENV_FILE, PROJECT_ROOT

load_dotenv(ENV_FILE)

# ==========================================
# Google Cloud Configuration
# ==========================================
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

# ==========================================
# Vetex Models
# ==========================================
TEXT_EMBEDDING_MODEL = "gemini-embedding-001"
SUMMARY_MODEL_GEMINI_2 = "gemini-2.5-flash-lite"
SUMMARY_MODEL_GEMINI_3 = "gemini-3-flash-preview"
# SUMMARY_MODEL_GEMINI_3 = "gemini-3-pro-preview"

# ==========================================
# Review Query Template
# ==========================================
GENERAL_REVIEW_QUERY = [
    "ordered {ITEM}",
    "the {ITEM} was",
]

# ==========================================
# Prompt Template
# ==========================================
with open(os.path.join(PROJECT_ROOT, 'core/text_review_labeling', 'prompt_template.txt'), 'r') as file:
    PROMPT_TEMPLATE = file.read()

DIETARY_OPTIONS_ALL = ["vegan", "gluten-free", "dairy-free", "nut-free", "egg-free", "vegetarian", "halal", "kosher"]