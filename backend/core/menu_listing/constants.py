import os
import json
from dotenv import load_dotenv
from utils.path_utils import PROJECT_ROOT, ENV_FILE

# Load environment variables from the project root's .env file
load_dotenv(ENV_FILE)

# ==========================================
# Google Cloud Configuration
# ==========================================
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_REGION")

# ==========================================
# Restaurant & Place ID Mapping
# ==========================================
with open(PROJECT_ROOT / "data" / "mapping.json", "r") as f:
    PID_RNAME_MAPPING = json.load(f)
RNAME_PID_MAPPING = {v: k for k, v in PID_RNAME_MAPPING.items()}

# ==========================================
# Menu Board Search and reduction Parameters
# ==========================================
EMBED_DIM = 128
MIN_DATE = "2024-01-01"
MIN_ISMENUBOARD_SIMILARITY = 0.355

TOP_K = 10
N_CLUSTER = 4

# ==========================================
# Query Vectors for Menu Board Classification
# ==========================================

QUERIES = {
    "is_menu": {
        "text": (
    "A photo of a full restaurant menu showing all menu items and prices, "
    "with the entire menu visible in frame and little surrounding background, "
    "organized for customer ordering."
        )
    # "A straight-on overview image of an entire restaurant menu, showing all menu items and prices together in one complete, readable layout."
    },
    "is_interior": {
        "text": (
            "An overview image of a restaurant dining space capturing the interior layout and ambiance."
        )
    },
    "is_exterior": {
        "text": (
            "A street-level view of a restaurant exterior with the storefront, entrance, and clearly visible restaurant logo or sign."
        )
    },
    "is_food": {
        "text": (
            "A detailed food photo showing plated dish or dishes as served, with textures and ingredients clearly visible."
        )
    }
}
with open(PROJECT_ROOT / "core" / "menu_listing" / "query_vectors.json", "r") as f:
    vectors_data = json.load(f)

def get_query_vector(dim: int, query_text: str):
    query_vector = None
    for entry in vectors_data:
        if entry["text"] == query_text:
            query_vector = entry[str(dim)]
            break
    
    if query_vector is None:
        print(f"Query vector for {query_text} not found. Generating...")
        from menu_listing.precompute import generate_and_save_vectors
        query_vector = generate_and_save_vectors(query_text)[dim]
    
    return query_vector

for query_purpose, query_info in QUERIES.items():
    query_text = query_info["text"]
    query_vector = get_query_vector(EMBED_DIM, query_text)
    QUERIES[query_purpose]["vector"] = query_vector


# ==========================================
# Review Image Analytics
# ==========================================
# Options: "gemini-2.5-flash", "gemini-2.5-pro", "gemini-3-pro-preview"
GEMINI_MODEL = "gemini-3-flash-preview"
with open(PROJECT_ROOT / "core" / "menu_listing" / "menu_read_prompt.txt", "r") as f:
    MENU_READ_PROMPT = f.read()

# ==========================================
# Other Constants
# ==========================================
MAX_SIDE = 1024