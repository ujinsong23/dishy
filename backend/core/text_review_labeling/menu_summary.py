import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from text_review_labeling.gemini_calls import _call_gemini_v3
import json
import time
import pandas as pd
from typing import Dict
from concurrent.futures import ThreadPoolExecutor
import vertexai

from text_review_labeling.constants import (
    GCP_PROJECT_ID,
    GCP_LOCATION,
    PROMPT_TEMPLATE,
    DIETARY_OPTIONS_ALL
)
from text_review_labeling.schema import MenuReviewSummary
from utils.helpers import get_curr_time
from utils.path_utils import MENU_METADATA_PATH_TEMPLATE

vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

def load_base_menu(place_id: str) -> Dict[str, Dict]:
    """Loads the updated menu metadata structure."""
    menu_file = MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id)
    if not menu_file:
        print(f"Warning: Base menu file not found for {place_id}")
        return {}

    print(f"[{get_curr_time()}] Loading menu metadata from {menu_file}")

    with open(menu_file, 'r') as f:
        data = json.load(f)
        return data  # Return the whole structure: { "i": {"from_menuboard": item, "from_reviews": None} }

def leave_only_relevant_evidence_ids(menu_from_reviews: Dict[str, Dict]) -> Dict[str, Dict]:
    relevant_review_ids = menu_from_reviews['relevant_review_ids']

    # check diff_notes
    for diff_note in menu_from_reviews['diff_notes']:
        evidence_ids = diff_note["evidence_review_ids"]
        if not any(evidence_id in relevant_review_ids for evidence_id in evidence_ids):
            menu_from_reviews['diff_notes'].remove(diff_note)
            continue

        diff_note["evidence_review_ids"] = [evidence_id for evidence_id in evidence_ids
                                            if evidence_id in relevant_review_ids]

    # check dietary_claims
    for do in DIETARY_OPTIONS_ALL:
        if do not in menu_from_reviews['dietary_claims']:
            menu_from_reviews['dietary_claims'][do] = None
            continue
        
        claims = menu_from_reviews['dietary_claims'][do]
        if claims is None: continue

        for evidence in claims['evidences']:
            if evidence['review_id'] not in relevant_review_ids:
                claims['evidences'].remove(evidence)
        if not claims['evidences']:
            menu_from_reviews['dietary_claims'][do] = None

    return menu_from_reviews

def consolidate_dietary_info(menu: Dict[str, Dict]) -> Dict[str, str]:
    """Consolidate dietary information from multiple menu items."""
    consolidated_info = {do: None for do in DIETARY_OPTIONS_ALL}
    labels_from_menuboard = menu['from_menuboard']['dietary_labels']
    claims_from_reviews = menu['from_reviews']['dietary_claims']
    for do in DIETARY_OPTIONS_ALL:
        menuboard_mentioned = do in labels_from_menuboard
        
        review_claim = claims_from_reviews.get(do)
        llm_adherence = None
        evidences = []
        
        if review_claim:
             llm_adherence = review_claim.get('is_adherent')
             evidences = review_claim.get('evidences', [])

        final_tag = None
        
        if menuboard_mentioned:
            if llm_adherence is True:
                final_tag = 'verified'
            elif llm_adherence is False:
                final_tag = 'warning'
            else:
                final_tag = 'not_verified'
        else: 
            if llm_adherence is True:
                final_tag = 'info'
            # If llm_adherence is False or None, we discard (keep as None)

        if final_tag:
             consolidated_info[do] = {'tag': final_tag, 'evidences': evidences}
            
    return consolidated_info

def _process_single_menu(menu_id, df_labeled, full_menu_data):
    """Worker function to process a single menu item."""
    col_name = menu_id if menu_id in df_labeled.columns else str(menu_id)
    if col_name not in df_labeled.columns:
        return None
        
    matched_df = df_labeled[df_labeled[col_name] == 1]
    
    if matched_df.empty:
        print(f"[{get_curr_time()}] Menu {menu_id}: No matched reviews, skipping")
        return None

    print(f"[{get_curr_time()}] Menu {menu_id}: Analyzing {len(matched_df)} reviews...")

    # Extract original info from the new structure
    menu_info_from_menuboard = full_menu_data.get(str(menu_id), {})['from_menuboard']
    menu_name = menu_info_from_menuboard['name']
    sibling_menu_items = "\n-".join([
        v['from_menuboard']['name']+f"({v['from_menuboard']['description']})" if v['from_menuboard'].get('description') else v['from_menuboard']['name']
        for v in full_menu_data.values() if v['from_menuboard'].get('name') != menu_name
    ])
    reviews_combined = "\n\n".join(
        [f"Review ID - {idx}: {row['text']}" for idx, row in matched_df.iterrows()]
    )
    prompt = PROMPT_TEMPLATE.format(
        menu_name=menu_name,
        menu_info_from_menuboard={k: v for k, v in menu_info_from_menuboard.items() if k not in ['name', 'dietary_labels']},
        sibling_menu_items = "-" + sibling_menu_items,
        reviews_combined=reviews_combined,
    )

    max_attempts = 5
    sleep_time = 20
    for attempt in range(max_attempts):
        try:
            summary_dict = _call_gemini_v3(prompt, MenuReviewSummary)
            return summary_dict
        except Exception as e:
            status_code = getattr(e, 'code', None) or getattr(e, 'status_code', None)
            if status_code == 429:
                if attempt < max_attempts - 1:
                    print(f"[{get_curr_time()}] Menu {menu_id}: 429 Error - Retrying in {sleep_time}s (Attempt {attempt + 1}/{max_attempts})")
                    time.sleep(sleep_time)
                    continue
                else:
                    print(f"[{get_curr_time()}] Menu {menu_id}: Max retries reached for 429 Error.")
                    return None
            else:
                print(f"[{get_curr_time()}] Menu {menu_id}: Error - {str(e)}")
                return None
    return None


def generate_menu_summaries(place_id: str, df_labeled: pd.DataFrame):
    """
    Generate review-based summaries and updates the menu metadata.
    """

    # 0. Load Menu Metadata
    full_menu_data = load_base_menu(place_id)
    if not full_menu_data:
        return []

    # 1. Identify menu items to process (keys in full_menu_data)
    menu_keys = list(full_menu_data.keys())

    print(f"\n=== Generating Menu Review Summaries ===")
    print(f"[{get_curr_time()}] Found {len(menu_keys)} menus to analyze")

    # 2. Process each menu in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Create a mapping of future to key to update the correct entry
        future_to_key = {
            executor.submit(_process_single_menu, k, df_labeled, full_menu_data): k
            for k in menu_keys
        }
        
        for future in future_to_key:
            k = future_to_key[future]
            try:
                res = future.result()
                if res:
                    full_menu_data[k]['from_reviews'] = leave_only_relevant_evidence_ids(res)
                    full_menu_data[k]['dietary_options'] = consolidate_dietary_info(full_menu_data[k])
            except Exception as e:
                print(f"[{get_curr_time()}] Menu {k}: Unexpected error - {str(e)}")

    for menu_id, menu in full_menu_data.items():
        dietary_labels = menu['from_menuboard']['dietary_labels']
        if menu['from_reviews'] is None:
            for do in DIETARY_OPTIONS_ALL:
                full_menu_data[menu_id]['dietary_options'] = {do: {'tag': 'not_verified', 'evidences': []} if do in dietary_labels else None for do in DIETARY_OPTIONS_ALL}

    # 3. Save updated results back to MENU_METADATA_PATH_TEMPLATE
    output_path = MENU_METADATA_PATH_TEMPLATE.format(place_id=place_id)

    n_mentioned = dict(
        (menu_id, 0 if menu['from_reviews'] is None else len(menu['from_reviews']['relevant_review_ids']) )
        for menu_id, menu in full_menu_data.items()
    )
    full_menu_data_sorted = dict(sorted(full_menu_data.items(), key=lambda x: n_mentioned[x[0]], reverse=True))
    
    with open(output_path, 'w') as f:
        json.dump(full_menu_data_sorted, f, indent=4)

    print(f"\n[{get_curr_time()}] Completed analysis for {len(menu_keys)} menus")
    print(f"[{get_curr_time()}] Saved results to {output_path}")

    return list(full_menu_data.values())
