import os
import os.path as osp
import json
import datetime
from datetime import timedelta
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import normalize
from collections import defaultdict

import vertexai
from menu_listing.gemini_calls import _call_gemini_v2, _call_gemini_v3
from menu_listing.constants import (
    GCP_PROJECT_ID, 
    GCP_LOCATION, 
    GEMINI_MODEL,
    EMBED_DIM, 
    QUERIES,
    TOP_K,
    N_CLUSTER,
    MIN_DATE,
    MIN_ISMENUBOARD_SIMILARITY,
    MENU_READ_PROMPT
)
from utils.path_utils import MENU_METADATA_PATH_TEMPLATE
from utils.helpers import get_curr_time
from menu_listing.schema import MenuExtractionResponse

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

def _calculate_similarity(df: pd.DataFrame, query_purpose: str) -> pd.DataFrame:
    """Calculates cosine similarity between menu board query and image embeddings."""
    col_name = f"embedding_{EMBED_DIM}"
    score_col =  f"{query_purpose}_similarity_{EMBED_DIM}"
    
    query_vec = np.array(QUERIES[query_purpose]["vector"])
    query_norm = np.linalg.norm(query_vec)
    
    embeddings_matrix = np.stack(df[col_name].values)
    embeddings_norm = np.linalg.norm(embeddings_matrix, axis=1)
    
    dot_products = np.dot(embeddings_matrix, query_vec)
    
    denominators = embeddings_norm * query_norm
    denominators[denominators == 0] = 1e-9
    
    similarities = dot_products / denominators
    
    df[score_col] = similarities
    return df

def _filter_results_with_backoff(
    df_sorted: pd.DataFrame, 
    query_purpose: str
) -> List[Dict[str, Any]]:
    """Applies date-based backoff logic to filter results."""
    col_name = f"embedding_{EMBED_DIM}"
    score_col =  f"{query_purpose}_similarity_{EMBED_DIM}"
    
    current_min_date = datetime.date.fromisoformat(MIN_DATE)
    min_results_target = TOP_K // 2
    max_backoff_attempts = 5
    
    final_results = []
    all_results_list = df_sorted.to_dict('records')

    for attempt in range(max_backoff_attempts + 1):
        temp_results = []
        
        for row in all_results_list:
            if len(temp_results) >= TOP_K:
                break
                
            score = row[score_col]
            
            # 1. Similarity Checker
            if score < MIN_ISMENUBOARD_SIMILARITY:
                break
                
            # 2. Date Checker
            p_date = row['published_date']
            row_date = None
            if p_date:
                if isinstance(p_date, datetime.date):
                    row_date = p_date
                elif isinstance(p_date, str):
                    try:
                        row_date = datetime.date.fromisoformat(p_date)
                    except:
                        pass
                elif isinstance(p_date, pd.Timestamp):
                    row_date = p_date.date()
            
            if row_date and row_date >= current_min_date:
                temp_results.append({
                    score_col: float(score),
                    "published_date": row_date.isoformat(),
                    "image_url": row['image_url'],
                    col_name: row[col_name]
                })
        
        # Check if we met the target
        if len(temp_results) >= min_results_target:
            final_results = temp_results
            break
            
        # Backoff: allow 6 months older
        current_min_date -= timedelta(days=6*30)
        if attempt < max_backoff_attempts:
            pass 
        else:
            final_results = temp_results
            
    return final_results

def search_menu_boards(
    df: pd.DataFrame
):
    """
    Searches for menu board images using text embedding.
    """
    
    print(f"\n\n=== Relevant Image Retrieval ===")
    print(f"[{get_curr_time()}] Searching maximum {TOP_K} images that best match query: '{QUERIES['is_menu']['text']}'...")
    
    # 1. Load Parquet
    if df.empty: return []

    # 2. Calculate Similarity
    df_sorted = _calculate_similarity(df, 'is_menu').sort_values(by=f"is_menu_similarity_{EMBED_DIM}", ascending=False)
    
    # 3. Filter with Backoff
    return _filter_results_with_backoff(df_sorted, 'is_menu')

def filter_non_food_images(df: pd.DataFrame) -> pd.DataFrame:
    """Filters out images that are unlikely to contain food menus."""
    assert f"is_menu_similarity_{EMBED_DIM}" in df.columns, "Similarity column not found in DataFrame."
        
    for query_purpose in ['is_interior', 'is_exterior', 'is_food']:
        df = _calculate_similarity(df, query_purpose)
    
    threshold = 0.33
    food_idx = (
        ((df[f'is_menu_similarity_{EMBED_DIM}'] < threshold)
         & (df[f'is_exterior_similarity_{EMBED_DIM}'] < threshold)
         & (df[f'is_interior_similarity_{EMBED_DIM}'] < threshold))
        | ((df[f'is_food_similarity_{EMBED_DIM}'] > 0.3)
           &(df[f'is_food_similarity_{EMBED_DIM}'] > df[f'is_menu_similarity_{EMBED_DIM}']-0.2))
    )

    df['likely_food']=food_idx
    print(f"[{get_curr_time()}] Tagged likely food images({food_idx.sum()}/{len(df)}) by threshold={threshold} to embeddings database.")
    
    return df.drop(columns=[col for col in df.columns if 'similarity' in col])

def prepare_url_date_pairs(search_results: List[Dict[str, Any]], n_cluster: int) -> Tuple[List[str], List[str]]:
    
    col_name = f"embedding_{EMBED_DIM}"

    if n_cluster is None or len(search_results) <= n_cluster:
        return (
            [entry['image_url'] for entry in search_results[:TOP_K]],
            [entry['published_date'] for entry in search_results[:TOP_K]]
        )
    else:
        print(f"[{get_curr_time()}] Clustering {len(search_results)} images into {n_cluster} clusters...")
        X = np.array([d[col_name] for d in search_results[:TOP_K]])
        X_norm = normalize(X)

        cluster_model = AgglomerativeClustering(n_clusters=n_cluster, metric='euclidean', linkage='ward')
        labels = cluster_model.fit_predict(X_norm)
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            date = search_results[i]['published_date']
            url = search_results[i]['image_url']
            clusters[label].append((str(date), url))
        
        selected_images = []
        selected_dates = []
        
        for label, cluster in clusters.items():
            cluster.sort(key=lambda x: x[0], reverse=True)
            selected_images.append(cluster[0][1])
            selected_dates.append(cluster[0][0])
        return selected_images, selected_dates

def _download_images(image_urls: List[str]) -> List[bytes]:
    """Downloads images from a list of URLs."""
    image_data = []
    for url in image_urls:
        try:
            import requests
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                image_data.append(resp.content)
        except Exception as e:
            print(f"[{get_curr_time()}] Failed to fetch image {url}: {e}")
    return image_data

def extract_menu_from_images(search_results, place_id: str) -> List[Dict[str, Any]]:
    """
    Takes a list of image URLs and uses Gemini to extract menu items.
    Aggregates menu name, price, and other details.
    """
    print("\n=== Menu Extraction (Gemini) ===")
    image_urls, image_dates = prepare_url_date_pairs(search_results, N_CLUSTER)

    prompt = MENU_READ_PROMPT
    
    print(f"[{get_curr_time()}] Preparing Gemini prompt by loading {len(image_urls)} images...")
    
    image_data = _download_images(image_urls)
    
    if not image_data:
        print(f"[{get_curr_time()}] Failed to download any images for Gemini.")
        return []

    try:
        if "gemini-3" in GEMINI_MODEL: menu_items = _call_gemini_v3(image_data, prompt, image_dates)
        else: menu_items = _call_gemini_v2(image_data, prompt, image_dates)
        
        if not menu_items:
            return []

        print(f"[{get_curr_time()}] Successfully extracted {len(menu_items)} items")

        output_json = MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id)
        print(f"[{get_curr_time()}] Saving menus.json to: {output_json}")
        os.makedirs(osp.dirname(output_json), exist_ok=True)
        
        output_dict = dict()
        for i, item in enumerate(menu_items):
            output_dict[i] = {'from_menuboard': item}
            output_dict[i]['from_reviews'] = None
            
        with open(output_json, "w") as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False)
        print(f"[{get_curr_time()}] Extracted menu data saved to: {output_json}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[{get_curr_time()}] Gemini extraction failed: {e}")
        return []