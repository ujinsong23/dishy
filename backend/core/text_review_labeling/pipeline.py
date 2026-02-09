import argparse
import json
import pandas as pd
import numpy as np
import warnings
import time
from sklearn.metrics.pairwise import cosine_similarity

from text_review_labeling.constants import (
    GENERAL_REVIEW_QUERY
)
from text_review_labeling.embedding import (
    generate_text_embeddings_from_json,
    get_query_embeddings,
    build_review_queries
)
from text_review_labeling.menu_summary import generate_menu_summaries
from utils.helpers import get_curr_time
from utils.path_utils import MENU_METADATA_PATH_TEMPLATE

warnings.filterwarnings("ignore")
pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', None)

def load_menu_listing(place_id: str):
    """Loads processed menu data from menus.json."""
    menu_file = MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id)
    print(f"[{get_curr_time()}] Loading processed menu from {menu_file}...")
    
    try:
        with open(menu_file, 'r') as f:
            data = json.load(f)
            
            menu_listing = []
            for menu_id, entry in data.items():
                item = entry.get('from_menuboard', {})
                name = item.get('name')
                nicknames = item.get('nicknames', [])
                if name:
                    menu_listing.append({
                        "id": str(menu_id), # Use the dictionary key as ID
                        "menu_name": [name] + nicknames
                    })
            return menu_listing
    except Exception as e:
        print(f"Error loading menu JSON: {e}")
        return []

def compute_max_similarities(df_reviews, df_menu):    
    if df_reviews.empty or df_menu.empty:
        return pd.DataFrame()
        
    review_embs = np.stack(df_reviews['embedding'].values)
    menu_embs = np.stack(df_menu['embedding'].values)
    
    similarities = cosine_similarity(review_embs, menu_embs)
    sim_df = pd.DataFrame(similarities, columns=df_menu['menu_id'])
    
    # Group by menu_id and take max similarity if multiple queries per menu
    sim_df_grouped = sim_df.T.groupby(level=0).max().T    
    sim_df_grouped.insert(0, 'text', df_reviews['text'].values)

    return sim_df_grouped

def find_optimal_threshold(sim_df, max_matches_per_menu):
    thresholds = np.arange(0.60, 0.90, 0.01)
    menu_columns = [col for col in sim_df.columns if col != 'text']
    optimal_threshold = 0.70 # Default
    
    for threshold in thresholds:
        match_counts = {}
        for menu_id in menu_columns:
            match_count = (sim_df[menu_id] >= threshold).sum()
            match_counts[menu_id] = match_count
        
        if not match_counts:
            continue
            
        max_matches = max(match_counts.values())
        if max_matches <= max_matches_per_menu:
            optimal_threshold = threshold
            break
    
    optimal_threshold = round(optimal_threshold, 2)
    df_labeled = sim_df.copy()
    for menu_id in menu_columns:
        df_labeled[menu_id] = (df_labeled[menu_id] >= optimal_threshold).astype(int)
    
    return optimal_threshold, df_labeled


def filter_top_20(df_labeled):
    # based on the number of true values in each column, filter top 20 columns
    menu_ids = [col for col in df_labeled.columns if col != 'text']
    print(df_labeled.columns)
    menu_id_counts = df_labeled[menu_ids].sum()
    menu_id_counts = menu_id_counts.sort_values(ascending=False)
    menu_id_counts = menu_id_counts.head(20) # todo: revert
    df_labeled = df_labeled[['text'] + list(menu_id_counts.index)]
    return df_labeled


def review_text_embeddings(place_id):
    """Generate and return review embeddings before menu processing."""
    print(f"\n[{get_curr_time()}] --- Starting Review Text Embeddings for {place_id} ---")
    
    # Generate embeddings for reviews
    processed_reviews = generate_text_embeddings_from_json(place_id=place_id)
    
    if not processed_reviews:
        print(f"[{get_curr_time()}] No reviews with text found. Exiting.")
        return None
    
    df_reviews = pd.DataFrame(processed_reviews)
    return df_reviews


def match_and_summarize_top_20(place_id, df_reviews):
    """Match reviews to menu items, filter top 20, and generate menu summaries."""
    print(f"\n[{get_curr_time()}] --- Starting Match and Filter for {place_id} ---")
    start_time = time.time()
    
    # Load menu listing
    menu_listing = load_menu_listing(place_id)
    if not menu_listing:
        print(f"[{get_curr_time()}] No menu items found. Exiting.")
        return None
    
    # Prepare menu queries
    print(f"[{get_curr_time()}] Preparing menu query embeddings...")
    menu_queries = build_review_queries(menu_listing, GENERAL_REVIEW_QUERY)
    query_texts = [q['query'] for q in menu_queries]
    query_embs = get_query_embeddings(query_texts)
    
    df_menu = pd.DataFrame(menu_queries)
    df_menu['embedding'] = query_embs
    
    # Compute similarities & labels
    print(f"[{get_curr_time()}] Computing similarities...")
    sim_df = compute_max_similarities(df_reviews, df_menu)
    
    print(f"[{get_curr_time()}] Optimizing threshold and labeling...")
    max_match_percentage = 0.80
    max_matches_per_menu = int(len(df_reviews) * max_match_percentage)
    
    optimal_threshold, df_labeled = find_optimal_threshold(sim_df, max_matches_per_menu)
    
    print(f"[{get_curr_time()}] Recommended threshold: {optimal_threshold}")
    
    # Filter top 20
    df_labeled = filter_top_20(df_labeled)
    
    # Generate menu summaries
    generate_menu_summaries(place_id, df_labeled)
    
    total_time = time.time() - start_time
    print(f"[{get_curr_time()}] Match and filter completed in {total_time:.2f}s")
    
    return df_labeled


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--place_id", type=str, required=True, help="Google Place ID for the restaurant")
    args = parser.parse_args()

    # Step 1: Generate review embeddings
    df_reviews = review_text_embeddings(args.place_id)
    if df_reviews is None:
        print("Failed to generate review embeddings. Exiting.")
        exit(1)
    
    # Step 2: Match with menu and filter top 20 (includes menu summary generation)
    df_labeled = match_and_summarize_top_20(args.place_id, df_reviews)
    if df_labeled is None:
        print("Failed to match and filter reviews. Exiting.")
        exit(1)
