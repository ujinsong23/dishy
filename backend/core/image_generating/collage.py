import argparse
import os.path as osp
import os
import tqdm
import json

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

import requests
from io import BytesIO
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from menu_listing.constants import PID_RNAME_MAPPING
from image_generating.constants import EMBED_DIM, COLLAGE_TOPK, MAX_IMAGE_PER_REVIEW
from utils.path_utils import IMAGE_EMBEDDING_PATH_TEMPLATE, MENU_METADATA_PATH_TEMPLATE, COLLAGE_PATH_TEMPLATE, COLLAGE_SRC_PATH_TEMPLATE, SCRAPED_REVIEW_PATH_TEMPLATE
from utils.helpers import load_json, get_curr_time

import warnings
# Suppress specific Google/Vertex AI warnings globally
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
from vertexai.vision_models import MultiModalEmbeddingModel
mm_embedding_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")
verbose = False

def filter_menu_images(df, menu):    
    
    menu_image_idx = df['review_id'].isin([str(review_id) for review_id in menu['from_reviews']['relevant_review_ids']])
    menu_df = df[menu_image_idx & df['likely_food']].drop(columns=['likely_food', 'published_date'])
    if verbose:
        print(
            f"\n\n{len(menu['from_reviews']['relevant_review_ids'])} reviews mentioned <{menu   ['from_menuboard']['name']}>, found total {menu_image_idx.sum()} images "
            f"where {len(menu_df)} is identified as likely food images.")
        
    if len(menu_df) == 0: return menu_df
    image_embeddings = np.vstack(menu_df[f'embedding_{EMBED_DIM}'].to_list())
    
    query_text = menu['from_reviews']['appearance']
    query_embedding = mm_embedding_model.get_embeddings(
        contextual_text=query_text,
        dimension=EMBED_DIM
        ).text_embedding
    query_embedding = np.array(query_embedding).reshape(1, -1)

    menu_df['similarity'] = cosine_similarity(image_embeddings, query_embedding).reshape(-1)
    menu_df_filtered = pd.DataFrame()
    for review_id, group in menu_df.groupby('review_id'):
        topk = group.nlargest(MAX_IMAGE_PER_REVIEW, 'similarity')
        menu_df_filtered = pd.concat([menu_df_filtered, topk.drop(columns=[c for c in topk.columns if c.startswith('embedding_')])], axis=0)

    menu_df_filtered = menu_df_filtered.sort_values(by='similarity', ascending=False).reset_index(drop=True)

    return menu_df_filtered

def define_grid_dimensions(num_images):
    if num_images <= 3:
        return (1, num_images)
    elif num_images <= 6:
        return (2, (num_images + 1) // 2)
    else:
        return (3, (num_images + 2) // 3)

def get_review_url_dict(place_id):
    reviews = load_json(SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id))
    return {int(review['id']): review['reviewUrl'] for review in reviews}

def save_topk_and_collage(menu_df_filtered, place_id, menu_id):
    if len(menu_df_filtered) == 0: return None

    review_url_dict = get_review_url_dict(place_id)

    os.makedirs(osp.dirname(COLLAGE_SRC_PATH_TEMPLATE).format(place_id=place_id, menu_id=menu_id), exist_ok=True)
    images = []
    rank_review_url_pairs = {}
    for rank,  row in menu_df_filtered.iterrows():
        review_id = row['review_id']
        rank_review_url_pairs[rank] = review_url_dict[int(review_id)]
        response = requests.get(row['image_url'])
        img = Image.open(BytesIO(response.content)).convert("RGB")
        img.save(COLLAGE_SRC_PATH_TEMPLATE.format(place_id=place_id,
                                                  menu_id=menu_id,
                                                  rank= rank
                                                  ))
        images.append(img)
        if len(images) >= COLLAGE_TOPK:
            break
    
    with open(osp.join(osp.dirname(COLLAGE_SRC_PATH_TEMPLATE).format(place_id=place_id, menu_id=menu_id), 'src_review_urls.json'), "w") as f:
        json.dump(rank_review_url_pairs, f, indent=2)

    nrow, ncol = define_grid_dimensions(len(images))
    fig, axs = plt.subplots(nrow, ncol, figsize=(5*ncol, 5*nrow))

    for idx, ax in enumerate(np.array(axs).reshape(-1)):
        if idx < len(images):
            ax.imshow(images[idx])
        ax.axis('off')

    # Instance-level adjustment is thread-safe; global plt.subplots_adjust is not
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)
    
    save_path = COLLAGE_PATH_TEMPLATE.format(place_id=place_id, menu_id=menu_id)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # bbox_inches='tight' forces the removal of any remaining white space
    fig.savefig(save_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    return True

if __name__ == "__main__":
   
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--place_id", type=str, required=True, help="Google Place ID for the restaurant")
    argparser.add_argument("--menu_id", type=int, required=False, default=-1, help="Menu ID to generate collage for")
    argparser.add_argument("--verbose", '-v', action='store_true', help="Enable verbose output")
    args = argparser.parse_args()
    place_id = args.place_id
    menu_id = args.menu_id
    verbose = args.verbose

    print(f"=== Restaurant: {PID_RNAME_MAPPING[place_id]} ({place_id}) ===\n")

    parquet_path = IMAGE_EMBEDDING_PATH_TEMPLATE.format(place_id=place_id)  
    df = pd.read_parquet(parquet_path)
    assert 'likely_food' in df.columns, "Please run script to add 'likely_food' column first"

    menus = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id))
    
    assert menu_id in menus.keys() or menu_id == -1, f"Menu ID {menu_id} not found for place {place_id}"
    if menu_id == -1: menu_ids = list(menus.keys())
    else: menu_ids = [menu_id]

    pbar = tqdm.tqdm(menu_ids)
    for menu_id in pbar:
        menu = menus[menu_id]
        if verbose:
            print(f"Menu[{menu_id}] {menu['from_menuboard']['name']}")
            for source, menu_data in menu.items():
                print(f" -{source}")
                for k, v in menu_data.items():
                    if k != "name": print(f"\t{k}: {v}")
                print()
        else:
            pbar.set_description(f"Processing Menu[{menu_id}] {menu['from_menuboard']['name']}")

        menu_df_filtered = filter_menu_images(df, menu, max_image_per_review=2, embed_dim=EMBED_DIM)
        collage = collage_topk_images(menu_df_filtered, collage_topk=9)

        if collage is None:
            if verbose: print(f"No images found for Menu[{menu_id}] {menu['from_menuboard']['name']}, skipping collage generation.")
            continue

        os.makedirs(COLLAGE_PATH_TEMPLATE.format(place_id=place_id, menu_id=menu_id), exist_ok=True)
        collage_path = COLLAGE_PATH_TEMPLATE.format(place_id=place_id, menu_id=menu_id)
        collage.savefig(collage_path)
        plt.close(collage)
        if verbose: print(f"Collage saved to {collage_path}")