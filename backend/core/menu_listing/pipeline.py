import warnings
import json
# Suppress specific Google/Vertex AI warnings globally
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import argparse
from menu_listing.embedding import generate_image_embeddings_from_json
from menu_listing.menuscan import search_menu_boards, extract_menu_from_images, filter_non_food_images
from menu_listing.constants import EMBED_DIM, PID_RNAME_MAPPING
from utils.path_utils import IMAGE_EMBEDDING_PATH_TEMPLATE

def main(place_id):

    # 1. Generate Image Embeddings
    embeddings_df = generate_image_embeddings_from_json(
        place_id=place_id, 
        dimension=EMBED_DIM
    )

    # 2. Search Menu Boards (Local Search)
    search_results = search_menu_boards(embeddings_df)
    temp = [{k:v for k,v in dd.items() if not('embedding' in k)} for dd in search_results]
    with open(IMAGE_EMBEDDING_PATH_TEMPLATE.replace("image_embeddings.parquet", "menuboard_candidates.json").format(place_id=place_id), 'w') as f:
        json.dump(temp, f, indent=2)
    filter_non_food_images(embeddings_df).to_parquet(
        IMAGE_EMBEDDING_PATH_TEMPLATE.format(place_id=place_id),
        index=False
        )
    
    # 3. Extract Menu items using Gemini
    assert len(search_results) > 0, "No menu boards found for this place"
    extract_menu_from_images(search_results, place_id)

    return

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--place_id", type=str, required=True, help="Google Place ID for the restaurant")
    args = parser.parse_args()
    
    print("\n\n")
    print("-" * 50)
    print(f"RESTAURANT REQUESTED: ({args.place_id}) {PID_RNAME_MAPPING.get(args.place_id, 'Unknown')}")
    print("-" * 50)

    main(place_id=args.place_id)