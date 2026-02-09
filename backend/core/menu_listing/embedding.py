import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import json
import requests
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
import vertexai
from vertexai.vision_models import Image as VMImage
from vertexai.vision_models import MultiModalEmbeddingModel
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from menu_listing.constants import (
    GCP_PROJECT_ID, 
    GCP_LOCATION, 
    EMBED_DIM, 
    MAX_SIDE
)
from utils.path_utils import SCRAPED_REVIEW_PATH_TEMPLATE, IMAGE_EMBEDDING_PATH_TEMPLATE
from utils.helpers import get_curr_time
import time
import random

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

mm_embedding_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")

def get_image_embedding_from_url(image_url: str, dimension: int) -> Tuple[List[float], float, float]:
    """
    Downloads image from URL and generates embedding.
    Includes retry logic with exponential backoff.
    """
    max_retries = 5
    base_delay = 6  # seconds
    
    for attempt in range(max_retries + 1):
        download_start = time.time()
        try:
            # 1. Download Image
            response = requests.get(image_url, stream=True, timeout=10)
            
            if response.status_code == 429:
                raise requests.exceptions.RequestException("Rate limit hit (429)")
            response.raise_for_status()
            
            image_bytes = response.content
            image = VMImage(image_bytes)
            download_time = time.time() - download_start

            # 2. Generate Embedding
            embed_start = time.time()
            embedding_obj = mm_embedding_model.get_embeddings(
                image=image,
                dimension=dimension,
            )
            embedding = embedding_obj.image_embedding
            embedding_time = time.time() - embed_start
            
            return embedding, download_time, embedding_time

        except Exception as e:
            if attempt == max_retries:
                print(f"[{get_curr_time()}] Final failure for {image_url}: {e}")
                return None, 0.0, 0.0
            
            is_retryable = True
            
            if is_retryable:
                sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[{get_curr_time()}] Error for {image_url}: {e}. Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)

    return None, 0.0, 0.0

def load_or_create_parquet(file_path: str) -> pd.DataFrame:
    if os.path.exists(file_path):
        try:
            return pd.read_parquet(file_path)
        except Exception:
            print(f"[{get_curr_time()}] Corrupt parquet file found. creating new one.")
    
    return pd.DataFrame(columns=["review_id", "image_url", "published_date"])

def generate_image_embeddings_from_json(
    place_id: str,
    dimension: int = EMBED_DIM,
    max_workers: int = 20):
    """Parses JSON, generates embeddings in parallel, and saves to local Parquet."""
    
    col_name = f"embedding_{dimension}"
    json_path = SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id)
    assert os.path.exists(json_path), f"JSON file not found: {json_path}"
    
    parquet_path = IMAGE_EMBEDDING_PATH_TEMPLATE.format(place_id=place_id)
    
    print(f"\n\n=== Image Embedding (Local Parquet) ===")
    
    # 1. Load Reviews
    with open(json_path, 'r') as f:
        reviews = json.load(f)

    # 2. Extract Images
    all_images = []
    print(f"[{get_curr_time()}] Loading image urls from scraped reviews...")
    for review in reviews:
        review_id = review.get("id")
        p_at = review.get("publishedAtDate")
        p_date = None
        if p_at:
            try:
                dt = datetime.fromisoformat(p_at.replace('Z', '+00:00'))
                p_date = dt.date().isoformat()
            except ValueError:
                pass
        
        for url in review.get("reviewImageUrls", []):
            all_images.append({
                "review_id": review_id,
                "image_url": url + f"=s{MAX_SIDE}",
                "published_date": p_date
            })
            
    # Dedup
    unique_images_map = {item['image_url']: item for item in all_images}
    unique_images_list = list(unique_images_map.values())

    if not unique_images_list:
        print(f"[{get_curr_time()}] No images found in JSON.")
        return pd.DataFrame(columns=["review_id", "image_url", "published_date"]), parquet_path

    # 3. Load existing Parquet
    df = load_or_create_parquet(parquet_path)
    
    if col_name not in df.columns:
        df[col_name] = None
        df[col_name] = df[col_name].astype(object)

    # 4. Check for existing embeddings
    already_embedded_urls = set()
    source_df = pd.DataFrame(unique_images_list)
    
    df_lookup_cols = ["image_url", col_name]
    if "review_id" in df.columns:
        df_lookup_cols.append("review_id")
        merge_on = ["review_id", "image_url"]
    else:
        merge_on = ["image_url"]

    merged_df = pd.merge(source_df, df[df_lookup_cols], 
                         on=merge_on, 
                         how="left", 
                         suffixes=("", "_old"))
    
    def is_valid_embed(x):
        if x is None: return False
        if isinstance(x, (list, np.ndarray)) and len(x) > 0: return True
        return False

    done_mask = merged_df[col_name].apply(is_valid_embed)
    already_embedded_urls = set(merged_df[done_mask]['image_url'])
    
    if already_embedded_urls:
        print(f"[{get_curr_time()}] Found {len(already_embedded_urls)} images already embedded locally.")
    
    to_process = [img for img in unique_images_list if img['image_url'] not in already_embedded_urls]
    
    if not to_process:
        print(f"[{get_curr_time()}] All images are already embedded for this dimension! Skipping.")
        return df

    # 5. Parallel Processing
    print(f"[{get_curr_time()}] Processing {len(to_process)} images in parallel (Target Dim: {dimension}, Workers: {max_workers})...")
    
    results_map = {} # url -> embedding
    total_download_time = 0.0
    total_embedding_time = 0.0
    successful_embeds = 0

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(get_image_embedding_from_url, item['image_url'], dimension): item 
            for item in to_process
        }
        
        for future in tqdm(as_completed(future_to_item), total=len(to_process), desc="Embedding Images", unit="img"):
            item = future_to_item[future]
            try:
                embedding, down_time, embed_time = future.result()
                
                if embedding:
                    results_map[item['image_url']] = embedding
                    total_download_time += down_time
                    total_embedding_time += embed_time
                    successful_embeds += 1
                
            except Exception as e:
                print(f"[{get_curr_time()}] Error processing {item['image_url']}: {e}")

    end_time = time.time()

    # 6. Update DataFrame and Save
    current_entries = []
    
    existing_embed_map = {}
    if not df.empty and col_name in df.columns:
        temp_df = df.drop_duplicates(subset=['image_url'])
        existing_embed_map = temp_df.set_index('image_url')[col_name].to_dict()
    
    for img in unique_images_list:
        url = img['image_url']
        embed = None
        
        if url in results_map:
            embed = results_map[url]
        elif url in existing_embed_map:
            embed = existing_embed_map[url]
            
        img_entry = img.copy()
        img_entry[col_name] = embed
        current_entries.append(img_entry)

    new_df = pd.DataFrame(current_entries)
    
    if not df.empty:
        other_cols = [c for c in df.columns if c not in new_df.columns and c not in ["published_date", "review_id", "place_id"]]
        
        if other_cols:
            cols_to_fetch = ["image_url"] + other_cols
            existing_others = df[cols_to_fetch].drop_duplicates(subset=['image_url'])
            new_df = pd.merge(new_df, existing_others, on="image_url", how="left")   
    
    assert new_df[col_name].isnull().sum()==0, f"{col_name} has null values"
    # null_count = new_df[col_name].isnull().sum()
    # if null_count > 0:
    #     print(f"[{get_curr_time()}] WARNING: {null_count} images failed to embed even after retries.")

    # Save
    new_df.to_parquet(parquet_path, index=False)
    print(f"[{get_curr_time()}] Saved updated embeddings to {parquet_path}")

    # Performance Report
    if successful_embeds > 0:
        avg_dl = total_download_time / successful_embeds
        avg_emb = total_embedding_time / successful_embeds
        print(f"\n[{get_curr_time()}] Finished embedding images for dimension={dimension}.")
        print(f"\t-Avg Image Download Time: {avg_dl:.4f} sec")
        print(f"\t-Avg Vertex Embedding Time: {avg_emb:.4f} sec")
        print(f"\t-Total Iteration Time: {end_time - start_time:.2f} sec")
        
    return new_df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--place_id", type=str, required=True, help="Google Place ID for the restaurant")
    args = parser.parse_args()

    generate_image_embeddings_from_json(
        place_id=args.place_id
    )