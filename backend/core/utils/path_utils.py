from pathlib import Path

def _find_root() -> Path:
    """
    Search upwards for a marker file to find the project root.
    """
    # Start looking from the directory containing this file
    current_path = Path(__file__).resolve().parent
    for parent in [current_path] + list(current_path.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    
    # Fallback to current directory's parent if nothing found
    return current_path.parent

PROJECT_ROOT = _find_root()
DATA_DIR = PROJECT_ROOT / "data"
ENV_FILE = PROJECT_ROOT / ".env"

SCRAPED_REVIEW_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/reviews.json"
IMAGE_EMBEDDING_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/image_embeddings.parquet"
MENU_METADATA_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/menus.json"
REVIEWS_DF_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/reviews_df.pkl"
COLLAGE_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/collage/{menu_id}.png"
COLLAGE_SRC_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/collage_src/{menu_id}/{rank}.png"
NANOBANANA_IMAGE_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/nanobanana/{menu_id}.png"
RESTAURANT_OVERVIEW_PATH_TEMPLATE = str(DATA_DIR)+"/{place_id}/restaurant_overview.json"