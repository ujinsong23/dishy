import os
import os.path as osp
import sys
import pandas as pd
import time
import json
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
from flask import Flask, render_template, request, Response, jsonify, send_from_directory
import requests
from flask_cors import CORS

# Core pipeline imports
from core.review_scraping.pipeline import scrape_reviews
from core.menu_listing.pipeline import main as menu_listing_main
from core.text_review_labeling.pipeline import review_text_embeddings, match_and_summarize_top_20
from core.restuarant_overview.restauarnt_summary import summarize_restaurant_overview
from core.image_generating.pipeline import save_collage_parallel, generate_from_collage
from core.utils.path_utils import *
from core.utils.helpers import load_json
from datetime import datetime

app = Flask(__name__)
frontend_url = os.environ.get('FRONTEND_URL', '*')
CORS(app, resources={r"/*": {"origins": frontend_url}})
executor = ThreadPoolExecutor(max_workers=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "Plated AI Backend API is running"}), 200

@app.route('/log', methods=['POST'])
def log_message():
    print("hello", file=sys.stdout)
    sys.stdout.flush()
    return Response(status=204)


@app.route('/reviews', methods=['POST'])
def get_reviews():
    data = request.json or {}
    place_id = data.get('place_id')
    ids = data.get('ids')
    ids = [str(i) for i in ids]

    review_path = SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id)
    if not os.path.exists(review_path):
        return jsonify({'error': 'Reviews not found for this place'}), 404

    all_reviews = load_json(review_path)
    id_set = set(ids)
    by_id = {r.get('id'): r for r in all_reviews if r.get('id') in id_set}
    # Preserve order of requested ids
    out = []
    for rid in ids:
        r = by_id.get(rid)
        if not r:
            continue
        raw_date = r.get('publishedAtDate') or r.get('publishedDate') or ''
        try:
            dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
            published_date = dt.strftime('%Y/%m/%d')
        except (ValueError, TypeError):
            published_date = raw_date[:10].replace('-', '/') if raw_date else ''
        out.append({
            'text': r.get('text', ''),
            'reviewUrl': r.get('reviewUrl', ''),
            'publishedDate': published_date,
        })
    return jsonify({'reviews': out})


@app.route('/search_restaurants', methods=['GET'])
def search_restaurants():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
 
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        return jsonify({'error': 'Google Maps API key not configured'}), 500

    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': query,
            'key': api_key,
            'region': 'us',
            'type': 'restaurant'
        }
        response = requests.get(url, params=params)
        data = response.json()

        if data.get('status') != 'OK' and data.get('status') != 'ZERO_RESULTS':
            return jsonify({'error': data.get('status'), 'message': data.get('error_message')}), 500

        results = []
        for place in data.get('results', []):
            results.append({
                'name': place.get('name'),
                'address': place.get('formatted_address'),
                'place_id': place.get('place_id'),
                'rating': place.get('rating'),
                'user_ratings_total': place.get('user_ratings_total')
            })

        return jsonify({
            "result": results,
            "message": f"Found {len(results)} places."
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/review_scraping', methods=['POST'])
def run_review_scraping():
    data = request.json
    place_id = data.get('place_id')
    restaurant_name = data.get('restaurant_name')
    if not place_id: return jsonify({'error': 'Missing place_id'}), 400

    if osp.exists(SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id)): 
        print(f"Reviews already scraped for {place_id}")
        time.sleep(5)
    else:
        scrape_reviews(place_id)
    reviews = load_json(SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id))
    if len(reviews) < 200:
        return jsonify({
            'error': 'Insufficient reviews',
            'message': f'Expected at least 200 reviews, got {len(reviews)}.',
            'review_count': len(reviews),
        }), 400
    image_count = 0
    for review in reviews:
        image_count += len(review.get("reviewImageUrls", []))
    
    mapping = load_json(DATA_DIR / "mapping.json")
    mapping[place_id] = restaurant_name
    with open(DATA_DIR / "mapping.json", 'w') as f:
        json.dump(mapping, f, indent=2)
    
    return jsonify({
        "review_count": len(reviews),
        "image_count": image_count,
        "review_examples": reviews[:10],
        "message": f"Successfully scraped {len(reviews)} reviews."
    })

@app.route('/menu_listing_main', methods=['POST'])
def run_menu_listing_main():
    data = request.json
    place_id = data.get('place_id')
    if not place_id: return jsonify({'error': 'Missing place_id'}), 400

    try:
        if osp.exists(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id)):
            time.sleep(5)
        else:
            f1 = executor.submit(menu_listing_main, place_id)
            f2 = executor.submit(review_text_embeddings, place_id)
            
            f1.result()  # Wait for menu listing
            df_reviews = f2.result() # Wait for reviews df
            
            # Save reviews df locally for next steps
            save_path = REVIEWS_DF_PATH_TEMPLATE.format(place_id=place_id)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            df_reviews.to_pickle(save_path)

        menus = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id))
        
        return jsonify({
            "result": {"place_id": place_id},
            "menus": menus,
            "message": "Menu extracted and reviews embedded in parallel."
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/match_and_summarize_top_20', methods=['POST'])
def run_match_and_summarize():
    data = request.json
    place_id = data.get('place_id')
    save_path = REVIEWS_DF_PATH_TEMPLATE.format(place_id=place_id)
    
    try:
        if osp.exists(RESTAURANT_OVERVIEW_PATH_TEMPLATE.format(place_id=place_id)):
            time.sleep(5)
            restaurant_overview = load_json(RESTAURANT_OVERVIEW_PATH_TEMPLATE.format(place_id=place_id))
        else:
            df_reviews = pd.read_pickle(save_path)
            df_labeled = match_and_summarize_top_20(place_id, df_reviews)
            
            top_dishes = [col for col in df_labeled.columns if col != 'text']
            restaurant_overview = summarize_restaurant_overview(place_id)
        
        menus = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id))
        
        return jsonify({
            "result": {"place_id": place_id},
            "menus": menus,
            "restaurant_overview": restaurant_overview,
            "message": "Success"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/collage_images', methods=['POST'])
def run_collage_images():
    data = request.json
    place_id = data.get('place_id')
    if not place_id:
        return jsonify({'error': 'Missing place_id'}), 400
    
    save_collage_parallel(place_id)

    collage_images = {}
    src_review_urls = {}
    collage_dir = osp.dirname(osp.dirname(COLLAGE_SRC_PATH_TEMPLATE)).format(place_id=place_id)
    for menu_id in os.listdir(collage_dir):
        menu_path = osp.join(collage_dir, menu_id)
        
        collage_images[menu_id] = []
        src_review_urls[menu_id] = []

        rank_urls_dict = load_json(osp.join(menu_path, "src_review_urls.json"))
        for rank, url in rank_urls_dict.items():
            src_review_urls[menu_id].append(url)
            collage_images[menu_id].append(f"{rank}.png")
    
    return jsonify({
        "collage": collage_images,
        "src_review_urls": src_review_urls,
        "message": "Collage images retrieved."
    })


@app.route('/nanobanana_image', methods=['POST'])
def run_nanobanana_image():
    data = request.json or {}
    place_id = data.get('place_id')
    menu_id = data.get('menu_id')
    if not place_id or not menu_id:
        return jsonify({
            "status": "failed",
            "error": "Missing place_id or menu_id",
            "message": "Request body must include place_id and menu_id.",
        }), 400

    try:
        if osp.exists(NANOBANANA_IMAGE_PATH_TEMPLATE.format(place_id=place_id, menu_id=menu_id)):
            time.sleep(7)
            success, msg = True, "Read nanobanana image from local file."
        else:
            success, msg = generate_from_collage(place_id, menu_id)
   
        if success:
            return jsonify({
                "status": "created",
                "nanobanana": f'{menu_id}.png',
                "message": msg or "Nanobanana image created.",
            }), 200
        # call_nanobanana() returned None — no image generated
        return jsonify({
            "status": "no_image",
            "error": "No image generated",
            "message": msg or "Nanobanana returned no image for this menu.",
        }), 404
    except Exception:
        return jsonify({
            "status": "failed",
            "error": "Nanobanana generation failed",
            "message": "Failed to generate image. Please try again later.",
        }), 500


@app.route('/results', methods=['GET'])
def get_results():
    place_id = request.args.get('place_id')
    if not place_id:
        return jsonify({'error': 'Missing place_id'}), 400
    
    try:
        menu_path = MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id)
        if not os.path.exists(menu_path):
            return jsonify({'error': 'Results not found for this restaurant'}), 404
            
        menus = load_json(menu_path)
        
        # Structure it for the frontend
        results = []
        for menu_id, details in menus.items():
            results.append({
                "id": menu_id,
                "title": details.get("name", f"Menu {menu_id}"),
                "description": details.get("description", ""),
                "imageUrl": f"/api/images/{place_id}/{menu_id}" # Placeholder or real path
            })
            
        return jsonify({
            "restaurant_name": "Restaurant Name", # Could be fetched from metadata
            "menus": results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/data/<place_id>/nanobanana/<filename>')
def serve_nanobanana(place_id, filename):
    if not filename.endswith('.png'):
        return "Not found", 404
    return send_from_directory(os.path.join(DATA_DIR, place_id, "nanobanana"), filename)


@app.route('/data/<place_id>/collage/<menu_id>/<filename>')
def serve_collage(place_id, menu_id, filename):
    if not filename.endswith('.png'):
        return "Not found", 404
    return send_from_directory(os.path.join(DATA_DIR, place_id, "collage_src", menu_id), filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
