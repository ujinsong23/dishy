import os
import re
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import random
import json
from text_review_labeling.gemini_calls import _call_gemini_v3
from restuarant_overview.schema import MenusOverviewSummary

from utils.helpers import get_curr_time, load_json
from utils.path_utils import MENU_METADATA_PATH_TEMPLATE, SCRAPED_REVIEW_PATH_TEMPLATE, PROJECT_ROOT, DATA_DIR, RESTAURANT_OVERVIEW_PATH_TEMPLATE

with open(os.path.join(PROJECT_ROOT, 'core/restuarant_overview', 'prompt_template.md'), 'r') as file:
    PROMPT_TEMPLATE = file.read()

def curate_menu_info(place_id: str):
    """
    RETURNS:
     For each menu items, return a dict with keys:
        - name
        - description written from menuboard
        - price
        - objective summary by reviews
        - number of reviews mentioning the item
        - up to 5 sample raw text reviews mentioning the item (for top 3 most mentioned items)
    """
    reviews = load_json(SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=place_id))
    menus = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id))
    
    menus_ = {}
    for rank, (menu_id, menu) in enumerate(menus.items()):
        n_mentions = 0 if menu['from_reviews'] is None else len(menu['from_reviews']['relevant_review_ids'])
        menus_[menu_id] = {'id': menu_id, 'n_mentions': n_mentions}
        for k,v in menu['from_menuboard'].items():
            if k in ['name', 'description', 'price']:
                menus_[menu_id][k] = v
        menus_[menu_id]['objective_summary'] = (menu['from_reviews'] or {}).get("objective_summary", "")
        if rank<3:
            menus_[menu_id]['reviews'] = []
            review_ids = menu['from_reviews']['relevant_review_ids'] if menu['from_reviews'] else []
            for review_id in random.sample(review_ids, k=min(5, len(review_ids))):
                menus_[menu_id]['reviews'].append(reviews[int(review_id)]['text'].strip().replace('\n', ' '))
    
    return menus_

def prepare_prompt(menus, restaurant_name):
    menu_lines = []
    for menu_id, data in menus.items():
        item_text = f"Menu item {data['id']}: {data['name']} ({data['n_mentions']} review mentioned)"
        item_text += f"\nPrice: {data['price']}"
        if 'reviews' in data and data['reviews']:
            item_text += f"\nDescription: {data['description']}"
            item_text += f"\nReview Summary: {data['objective_summary']}"
            item_text += "\nSample Reviews:"
            for rev in data['reviews']:
                item_text += f"\n- {rev.strip()}"
        
        menu_lines.append(item_text)
    
    menu_context = "\n\n".join(menu_lines)

    return PROMPT_TEMPLATE.format(
        restaurant_name=restaurant_name,
        menu_context=menu_context
    )

def postprocess_to_html(restaurant_overview):
    summary_text = restaurant_overview['summary']
    summary_html = re.sub(
        r'\[(.*?)\]\((.*?)\)', 
        r'<b class="\2">\1</b>', 
        summary_text
    )
    restaurant_overview['summary'] = re.sub(
        r'\[(.*?)\]\((.*?)\)', 
        r'\1', 
        restaurant_overview['summary']
    )
    restaurant_overview['summary_html'] = summary_html
    return restaurant_overview
    
def summarize_restaurant_overview(place_id):
    PID_RNAME_MAPPING = load_json(DATA_DIR / "mapping.json")
    restaurant_name = re.sub(r'[^\x00-\x7f]', '', PID_RNAME_MAPPING[place_id]).strip()
    
    print(f"[{get_curr_time()}] Summarizing restaurant overview for {restaurant_name}...")
    menus = curate_menu_info(place_id)
    prompt = prepare_prompt(menus, restaurant_name)
    restaurant_overview_json = _call_gemini_v3(prompt, MenusOverviewSummary, model="gemini-3-flash-preview")
    
    restaurant_overview_json = postprocess_to_html(restaurant_overview_json)
    
    json_path = RESTAURANT_OVERVIEW_PATH_TEMPLATE.format(place_id=place_id)
    with open(json_path, 'w') as f:
        json.dump(restaurant_overview_json, f, indent=4)
        
    print(f"[{get_curr_time()}] Saved restaurant overview JSON to {json_path}")
    return restaurant_overview_json

if __name__=="__main__":
    place_id = "ChIJT2NxLBPKj4ARRivowJnL3Wg"
    summarize_restaurant_overview(place_id)  