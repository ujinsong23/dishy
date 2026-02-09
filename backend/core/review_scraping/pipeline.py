import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv
from utils.path_utils import ENV_FILE, SCRAPED_REVIEW_PATH_TEMPLATE
from utils.helpers import load_json

load_dotenv(ENV_FILE)

def scrape_reviews(place_id: str):
    client = ApifyClient(os.getenv("APIFY_TOKEN"))

    run_input = {
        "placeIds": [place_id],
        "maxReviews": 500,
        "language": "en",
        "reviewsSort": "mostRelevant",
        "reviewsOrigin": "google",
        "personalData": True,
    }

    run = client.actor("compass/google-maps-reviews-scraper").call(run_input=run_input)

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    formatted = []
    for idx, item in enumerate(items):
        formatted.append({
            "id": str(idx),
            "text": item.get("text"),
            "publishedAtDate": item.get("publishedAtDate"),
            "reviewUrl": item.get("reviewUrl"),
            "reviewImageUrls": item.get("reviewImageUrls", []),
        })

    os.makedirs(os.path.dirname(SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id)), exist_ok=True)
    output_path = SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(formatted)} reviews to {output_path}")

    return formatted


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--place_id", type=str, default="ChIJ45nohjW1j4ARlHArHtlS5I0") # sweet maple= ChIJ45nohjW1j4ARlHArHtlS5I0
    args = parser.parse_args()
    
    place_id = args.place_id

    scrape_reviews(place_id)
