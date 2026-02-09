from core.review_scraping.pipeline import scrape_reviews
from core.menu_listing.pipeline import main as menu_listing_main
from core.text_review_labeling.pipeline import review_text_embeddings, match_and_summarize_top_20
from core.restuarant_overview.restauarnt_summary import summarize_restaurant_overview
from utils.helpers import load_json
from utils.path_utils import MENU_METADATA_PATH_TEMPLATE
from core.image_generating.pipeline import save_collage_parallel, generate_from_collage
from concurrent.futures import ThreadPoolExecutor

def run_end_to_end(place_id: str):
    # scrape_reviews(place_id)
    with ThreadPoolExecutor() as executor:
        future_menu = executor.submit(menu_listing_main, place_id)
        future_reviews = executor.submit(review_text_embeddings, place_id)
        
        # Wait for both to complete
        future_menu.result()
        df_reviews = future_reviews.result()
        
    match_and_summarize_top_20(place_id, df_reviews)
    summarize_restaurant_overview(place_id)

    save_collage_parallel(place_id)
    menus = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id))
    menus_sorted = sorted([(menu_id, menu) for menu_id, menu in menus.items() if menu['from_reviews'] is not None], key=lambda x: len(x[1]['from_reviews']['relevant_review_ids']), reverse=True)[:3]
    for menu_id, menu in menus_sorted:
        generate_from_collage(place_id, menu_id)
    return 'success'

if __name__ == "__main__":
    place_id = "ChIJT2NxLBPKj4ARRivowJnL3Wg" # paik's noodle
    place_id = "ChIJ45nohjW1j4ARlHArHtlS5I0" # Sweet maple
    # placE_id = "ChIJO79pfG7Kj4ARTnmoiEbJKEk" # Kunjip
    run_end_to_end(place_id)
