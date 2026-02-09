import streamlit as st
from utils.path_utils import *
from utils.helpers import load_json

st.set_page_config(page_title="Menu Metadata Viewer", page_icon="🍴", layout="wide")

st.title("🍴 Menu Metadata Quick Viewer")

PID_RNAME_MAPPING = load_json(DATA_DIR / "mapping.json")
RNAME_PID_MAPPING = {v: k for k, v in PID_RNAME_MAPPING.items()}

import os

# Emoji mapping for metadata
CATEGORY_EMOJIS = {
    "red_meat": "🥩",
    "poultry": "🍗",
    "fish": "🐟",
    "shellfish": "🦐",
    "allergen_ingredients": "🥜"
}

OPTION_EMOJIS = {
    "size": "📏",
    "spiciness": "🌶️",
    "toppings": "🤌",
    "proteins": "🥓",
    "other_option": "➕"
}

def format_ingredients(ingredients_dict):
    if not ingredients_dict:
        ingredients_dict = {}
    lines = []
    for cat, emoji in CATEGORY_EMOJIS.items():
        items = ingredients_dict.get(cat, [])
        content = ", ".join(items) if items else "-"
        lines.append(f"{emoji} {content}")
    return " | ".join(lines)

def format_options(options_dict):
    if not options_dict:
        options_dict = {}
    lines = []
    for opt_type, emoji in OPTION_EMOJIS.items():
        options = options_dict.get(opt_type, [])
        content = ", ".join([o.lower() for o in options]) if options else "-"
        lines.append(f"{emoji} **{opt_type}**: {content}")
    return "  \n".join(lines)

# Restaurant Selection
restaurant_options = list(RNAME_PID_MAPPING.keys())
default_index = 2 if len(restaurant_options) >= 3 else 0

# Controls Layout
ctrl_col1, ctrl_col2 = st.columns([2, 2])
with ctrl_col1:
    rname = st.selectbox("Choose restaurant:", options=restaurant_options, index=default_index, key="selected_restaurant")

PHASES = [
    "User query entered (0s)",
    "Scrapping done (60s)",
    "Menu extracted (120s)",
    "Reviews analyzed (128s)",
    "Collage created (140s)",
    "Nanobanana generated"
]

with ctrl_col2:
    selected_phase_name = st.select_slider("Select Data Phase", options=PHASES, value=PHASES[-1])
    phase = PHASES.index(selected_phase_name)


pid = RNAME_PID_MAPPING[rname]

menu_metadata = load_json(MENU_METADATA_PATH_TEMPLATE.format(place_id=pid))
reviews_data = load_json(SCRAPED_REVIEW_PATH_TEMPLATE.format(place_id=pid))

# ID to URL mapping
review_id_to_url = {str(r["id"]): r["reviewUrl"] for r in reviews_data}

if not menu_metadata:
    st.warning(f"No menu metadata found for {rname} (`{pid}`)")
    st.stop()

def get_linked_ids(ids):
    links = []
    for rid in ids:
        url = review_id_to_url.get(str(rid))
        if url:
            links.append(f"[#{rid}]({url})")
        else:
            links.append(f"#{rid}")
    return ", ".join(links)

if phase >= 1:
    # Phase 1: Reviews Dump
    with st.expander("📄 View Raw Reviews JSON", expanded=False):
        st.json(reviews_data)

if phase >= 2:
    # Menu Selection logic
    menu_ids = sorted(list(menu_metadata.keys()), key=lambda x: int(x) if x.isdigit() else x)
    menu_options = [f"{m_id}: {menu_metadata[m_id]['from_menuboard'].get('name', 'N/A')}" for m_id in menu_ids]

    # selected_option = st.selectbox("Select Menu Item to drill down:", options=menu_options)
    selected_menu = st.slider("select menu", min_value=0, max_value=len(menu_ids)-1, value=0, key="selected_menu")
    selected_id = menu_ids[selected_menu]
    st.markdown(f"### {selected_id}: {menu_metadata[selected_id]['from_menuboard'].get('name', 'N/A')}")

    menu_info = menu_metadata[selected_id]

    collage_path = COLLAGE_PATH_TEMPLATE.format(place_id=pid, menu_id=selected_id)
    nb_path = NANOBANANA_IMAGE_PATH_TEMPLATE.format(place_id=pid, menu_id=selected_id)

    has_collage = os.path.exists(collage_path)
    has_nb = os.path.exists(nb_path)
    
    mb = menu_info.get("from_menuboard", {})
    rv = menu_info.get("from_reviews")

    if phase >= 3:
        st.markdown("### 🥗 Dietary Analysis")
        if not rv or not isinstance(rv, dict):
            st.warning("⚠️ This menu didn't have enough reviews to analyze dietary claims.")
        else:
            dietary_options = ["vegan", "gluten-free", "dairy-free", "nut-free", "egg-free", "vegetarian", "halal", "kosher"]
            mb_labels = mb.get("dietary_labels", []) or []
            rv_claims = rv.get("dietary_claims", {}) or {}
            final_opts = menu_info.get("dietary_options", {}) or {}

            table_data = []

            def format_evidence_with_quotes(evidences):
                if not evidences:
                    return ""
                items = []
                for ev in evidences:
                    quote = ev.get('quote', '')
                    rid = ev.get('review_id', '')
                    link = get_linked_ids([rid])
                    items.append(f"('{quote}' {link})")
                return "  \n".join(items)

            for do in dietary_options:
                menu_icon = "📜" if do in mb_labels else "➖"
                
                claim = rv_claims.get(do)
                review_status = "➖"
                if claim:
                    adh = claim.get("is_adherent")
                    icon = "🟢" if adh is True else "🔴" if adh is False else "➖"
                    ev_str = format_evidence_with_quotes(claim.get("evidences", []))
                    review_status = f"{icon} {ev_str}" if ev_str else icon
                
                final_item = final_opts.get(do)
                final_status = "➖"
                if final_item:
                    tag = final_item.get("tag")
                    tag_map = {
                        "verified": "✅ Verified",
                        "warning": "⚠️ Warning",
                        "info": "ℹ️ Info",
                        "not_verified": "❓ Unverified"
                    }
                    display_tag = tag_map.get(tag, tag)
                    final_status = display_tag

                if menu_icon != "➖" or review_status != "➖" or (final_item is not None):
                    table_data.append({
                        "Option": do.capitalize(),
                        "Menu": menu_icon,
                        "Review Status": review_status,
                        "Final Result": final_status
                    })

            if table_data:
                # Use CSS to hide the row index in st.table
                st.markdown("""
                <style>
                thead tr th:first-child {display:none}
                tbody tr th {display:none}
                </style>
                """, unsafe_allow_html=True)
                st.table(table_data)
            else:
                st.write("None")
        st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 From Menuboard")
        
        st.markdown("#### Price")
        st.write(f"${mb.get('price', 'N/A')}")
        
        st.markdown("#### Nicknames")
        st.write(f"{', '.join(mb.get('nicknames', [])) if mb.get('nicknames') else 'N/A'}")
        
        st.markdown("#### Description")
        st.write(f"{mb.get('description', 'N/A')}")
        
        st.markdown("#### Options")
        st.write(format_options(mb.get("options", {})))
        
    with col2:
        if phase >= 3:
            st.markdown("### 💬 From Reviews")
            
            if not rv or not isinstance(rv, dict):
                st.warning("⚠️ This menu didn't have enough reviews to analyze (wasn't top 20).")
            else:
                st.markdown("#### Objective Summary")
                st.write(f"{rv.get('objective_summary', 'N/A')}")
                
                st.markdown("#### Appearance")
                st.write(f"{rv.get('appearance', 'N/A')}")
                
                st.markdown("#### Ingredients")
                st.write(format_ingredients(rv.get("ingredients_by_category", {})))
                
                st.markdown("#### Review Links")
                st.write(get_linked_ids(rv.get('relevant_review_ids', [])))
        
                if rv.get("diff_notes"):
                    st.markdown("#### Discrepancy Notes")
                    for note in rv.get("diff_notes", []):
                        st.write(f"- {note['note'].replace('`', '').replace('$','USD')} *(Evidence: {get_linked_ids(note['evidence_review_ids'])})*")
        else:
            st.empty()

    img_col1, img_col2 = st.columns(2)
    
    with img_col1:
        if phase >= 4:
            if has_collage:
                st.image(collage_path, caption="Original Collage", width="stretch")
            else:
                st.warning("❌ No source collage available")
        else:
            st.info("🖼️ *Collage: <image not ready on this phase>*")
            
    with img_col2:
        if phase >= 5:
            if has_nb:
                st.image(nb_path, caption="Generated Nanobanana Image", width="stretch")
            elif has_collage:
                    st.warning("⚠️ No relevant item detected for generation")
            else:
                st.warning("❌ Source missing")
        else:
            st.info("🖼️ *Nanobanana: <image not ready on this phase>*")

    # Legend
    st.divider()
    st.markdown("*<<Legend>>*")
    leg_col1, leg_col2, leg_col3 = st.columns(3)
    with leg_col1:
        st.markdown("**Ingredients:**")
        st.write("🥩 Red Meat | 🍗 Poultry | 🐟 Fish | 🦐 Shellfish | 🥜 Allergen")
    with leg_col2:
        st.markdown("**Options:**")
        st.write("📏 Size | 🌶️ Spiciness | 🤌 Toppings | 🥓 Proteins | ➕ Other")
    with leg_col3:
        st.markdown("**Analysis Status:**")
        st.markdown("📜 On Menu | 🟢 Review Safe | 🔴 Review Unsafe")
        st.markdown("✅ Verified | ⚠️ Warning | ℹ️ Info | ❓ Unverified")