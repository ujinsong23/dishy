import os
from dotenv import load_dotenv
from utils.path_utils import ENV_FILE, PROJECT_ROOT

# Load environment variables from the project root's .env file
load_dotenv(ENV_FILE)
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

EMBED_DIM = 128
COLLAGE_TOPK = 9
MAX_IMAGE_PER_REVIEW = 2

NANOBANANA_MODEL_NAME = 'gemini-3-pro-image-preview'
with open(os.path.join(PROJECT_ROOT, 'core/image_generating', 'prompt_template.txt'), 'r') as file:
    PROMPT_TEMPLATE = file.read()
