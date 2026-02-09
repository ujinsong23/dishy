import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from image_generating.collage import filter_menu_images, save_topk_and_collage
from image_generating.nanobanana import call_nanobanana, prepare_prompt
from image_generating.constants import NANOBANANA_MODEL_NAME
from utils.helpers import load_json, get_curr_time
from utils.path_utils import IMAGE_EMBEDDING_PATH_TEMPLATE, MENU_METADATA_PATH_TEMPLATE, COLLAGE_PATH_TEMPLATE, NANOBANANA_IMAGE_PATH_TEMPLATE

def generate_from_collage(place_id, menu_id):
    menus = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id))
    if menus is None or not isinstance(menus, dict):
        return False, "Menu metadata not found or invalid."
    if menu_id not in menus:
        return False, f"Menu {menu_id} not found in metadata."
    menu = menus[menu_id]
    prompt = prepare_prompt(menu)
    collage_path = COLLAGE_PATH_TEMPLATE.format(place_id=place_id, menu_id=menu_id)

    out = call_nanobanana(
        image_path=collage_path,
        prompt=prompt,
    )
    menu_name = (menu.get('from_menuboard') or {}).get('name') or menu_id
    if out is None:
        return False, f"Collage was found, but no image generated from [{menu_id}]{menu_name}"

    save_path = NANOBANANA_IMAGE_PATH_TEMPLATE.format(place_id=place_id, menu_id=menu_id)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as img_file:
        img_file.write(out)
    return True, f"Saved [{menu_id}]{menu_name}"

def save_collage_parallel(place_id):
    df = pd.read_parquet(IMAGE_EMBEDDING_PATH_TEMPLATE.format(place_id=place_id))
    menus = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id))
    
    print(f"\n\n=== Per Menu Image Generation ===")
    print(f"[{get_curr_time()}] Forming collage for {len(menus)} menus...")

    def _process_single_menu(place_id, menu_id, menu, df):
        try:
            filtered_df = filter_menu_images(df, menu)
            success = save_topk_and_collage(filtered_df, place_id=place_id, menu_id=menu_id)
            
            if not success:
                return False, f"No images found for Menu[{menu_id}] {menu['from_menuboard']['name']}, skipping collage generation."
            
            return True, None
        except Exception as e:
            return False, f"Error processing Menu[{menu_id}]: {str(e)}"
            
    tasks = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for menu_id, menu in menus.items():
            if menu['from_reviews'] is None: continue
            tasks.append(executor.submit(_process_single_menu, place_id, menu_id, menu, df))
            
        for future in tqdm(as_completed(tasks), total=len(tasks), desc="Processing Menus"):
            success, msg = future.result()
            if msg:
                tqdm.write(f"[{get_curr_time()}] {msg}")
    return

# def generate_popular(place_id):
#     popularity_sorted_menus = sorted(
#         [(menu_id, menu) for menu_id, menu in menus.items() if menu['from_reviews'] is not None],
#         key=lambda x: len(x[1]['from_reviews']['relevant_review_ids']),
#         reverse=True
#     )
#     popular_top_n = 3
#     print(f"[{get_curr_time()}] Generating dish image for top {popular_top_n} menus using {NANOBANANA_MODEL_NAME}..")
#     for menu_id, menu in popularity_sorted_menus[:popular_top_n]:
#         if menu['from_reviews'] is None: continue
#         success, msg = generate_from_collage(place_id, menu_id, menu)
#         print(f"[{get_curr_time()}] {msg}")
#     return

if __name__ == "__main__":
   
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--place_id", type=str, required=True, help="Google Place ID for the restaurant")
    args = argparser.parse_args()
    
    save_collage_parallel(args.place_id)
