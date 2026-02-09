import json
import time
from datetime import datetime
from typing import List, Dict

import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from tqdm import tqdm

from text_review_labeling.constants import (
    GCP_PROJECT_ID,
    GCP_LOCATION,
    TEXT_EMBEDDING_MODEL
)
from utils.helpers import get_curr_time
from utils.path_utils import SCRAPED_REVIEW_PATH_TEMPLATE
import os

vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
model = TextEmbeddingModel.from_pretrained(TEXT_EMBEDDING_MODEL)


def get_text_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generates text embeddings for a batch of strings."""
    try:
        inputs = [TextEmbeddingInput(text, task_type="RETRIEVAL_DOCUMENT") for text in texts]
        embeddings = model.get_embeddings(
            inputs
        )
        return [emb.values for emb in embeddings]
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return [[] for _ in texts]


def generate_text_embeddings_from_json(
    place_id: str,
    batch_size: int = 100
) -> List[Dict]:
    """Parses scraped JSON reviews and generates embeddings."""
    
    json_path = SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id)
    if not os.path.exists(json_path):
        print(f"[{get_curr_time()}] Warning: Scraped reviews file not found at {json_path}")
        return []
    
    with open(json_path, 'r') as f:
        reviews = json.load(f)

    to_process = []
    print(f"\n=== Text Review Embedding ===")
    print(f"[{get_curr_time()}] Loading text from processed reviews ({len(reviews)} total)...")
    
    for review in reviews:
        # Use the simple "id" added during preprocessing
        r_id = review.get("id")
        text = review.get("text", "")
        
        if not text or r_id is None:
            continue
            
        p_at = review.get("publishedAtDate")
        p_date = None
        if p_at:
            try:
                dt = datetime.fromisoformat(p_at.replace('Z', '+00:00'))
                p_date = dt.date().isoformat()
            except ValueError:
                pass
        
        to_process.append({
            "place_id": place_id,
            "review_id": str(r_id),
            "text": text[:1000],
            "published_date": p_date
        })

    if not to_process:
        print(f"[{get_curr_time()}] No reviews with text found in JSON.")
        return []

    print(f"[{get_curr_time()}] Generating embeddings for {len(to_process)} reviews in batches of {batch_size}...")
    for i in tqdm(range(0, len(to_process), batch_size), desc="Embedding Text"):
        batch = to_process[i:i+batch_size]
        texts = [b['text'] for b in batch]
        embeddings = get_text_embeddings_batch(texts)
        
        for j, emb in enumerate(embeddings):
            if emb:
                batch[j]['embedding'] = emb
        
        time.sleep(0.5) 

    return to_process

def build_review_queries(menu_list: List[Dict], query_templates: List[str]) -> List[Dict]:
    """Generates query variations for each menu item."""
    all_queries = []
    for menu in menu_list:
        for template in query_templates:
            for name in menu.get("menu_name", []):
                all_queries.append({
                    "menu_id": menu["id"],
                    "query": template.format(ITEM=name)
                })
    return all_queries

def get_query_embeddings(queries: List[str], batch_size: int = 250) -> List[List[float]]:
    """Generates embeddings for queries (task_type=RETRIEVAL_QUERY)."""
    all_embeddings = []
    
    for i in range(0, len(queries), batch_size):
        batch = queries[i:i+batch_size]
        inputs = [TextEmbeddingInput(q, task_type="RETRIEVAL_QUERY") for q in batch]
        embeddings = model.get_embeddings(inputs)
        all_embeddings.extend([emb.values for emb in embeddings])
        
        # Rate limit handling just in case
        if len(queries) > batch_size:
            time.sleep(0.1)
            
    return all_embeddings
