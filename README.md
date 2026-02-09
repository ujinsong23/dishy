# 🍽️ Dishy: A Snapshot is Worth a Thousand Reviews 

[🎥 Video](https://www.youtube.com/watch?v=BFW43AHxfLc) | [🕹️ Devpost Project](https://devpost.com/software/dishy-a-snapshot-is-worth-a-thousand-reviews?ref_content=my-projects-tab&ref_feature=my_projects) | [💻 Live Demo](https://mm-menu-review-unifier-frontend-757541932861.us-central1.run.app)

> **Note on terminology**: In this project, *dish* refers to a single menu item appears in a restaurant menu (e.g., “Pad Thai”, “Margherita Pizza”).

Dishy is a multimodal reasoning system powered by **Gemini 3** that transforms noisy, fragmented restaurant reviews and photos into a **unified, per-dish mental model**. Instead of forcing users to read hundreds of reviews—or rely on a few randomly sampled opinions—Dishy synthesizes how a dish is *most commonly perceived, described, and served*, both visually and semantically.

This project goes beyond generating a single representative image. Dishy constructs a **dish-centric knowledge layer** that captures what people collectively mean when they talk about a menu item: what it looks like, how it tastes, how it is prepared, common variations, and where opinions diverge.

![image](assets/portal.png)

## 🚩 Problem

### For Customers

* Restaurants often accumulate **hundreds or thousands of reviews**, but information about a *specific menu item* is sparsely scattered across them with no organizing structure.
* To understand what a menu item actually is, users must manually skim many reviews, hoping to encounter representative descriptions or photos.
* Many restaurants serve **foreign cuisines**, where menu items have native names, informal English translations, and multiple phonetic spellings.
* Simple keyword search frequently fails due to typos, alternative transliterations, or semantically similar but non-identical terms.
* As a result, customers struggle to build a clear mental model of unfamiliar dishes before ordering or visiting.

### For Restaurants

* Online listings often surface **misleading or low-quality customer-uploaded images** for menu items.
* Creating professional menu assets—food photography, menu boards, and menu websites—is expensive and operationally heavy.
* Menu items frequently lack **organized, per-item explanations** (e.g., what the dish is, key ingredients, preparation style, dietary considerations).
* This missing structure can cause potential customers to disengage, even if the restaurant would otherwise match their preferences.

The core challenge is not a lack of data, but **an overabundance of unorganized data** that is difficult for both customers and restaurant owners to interpret and use effectively.

## 💡 Core Insight & Impact

While individual reviews are fragmented and unstructured, **collective information about a menu item is consistent when properly aggregated**. Across many photos and review texts, there exists enough signal to infer what a dish typically looks like, what it contains, and how it is prepared.

Dishy treats menu understanding as a **multimodal organization and synthesis problem**, transforming scattered signals into a unified, per-dish representation. For each dish, the system generates:

1. A synthesized visual representation constrained by visual and textual consensus, reflecting how the dish is *typically* served rather than idealized marketing imagery.

2. A structured and normalized description distilled from many sources, including:

   * Core ingredients and preparation style
   * Verification of dietary restrictions
   * Customer comments about recommendation, additional costs, seasonal availability, etc.
   * Ordering options

![image](assets/detail_page.png)

Together, these outputs form a **per-dish mental database** that replaces the need to manually scan large volumes of reviews with a structured knowledge layer. This unified representation serves both customers and restaurants:

### For Customers: Effortless Exploration
* **Unified Mental Model:** Quickly understand what a menu item *actually is*, even for unfamiliar cuisines, without reading hundreds of fragmented reviews.
* **Semantic Discovery:** Search and discover dishes with various filters powered by organized dish knowledge base from Dishy.

### For Restaurants: Automated Asset Creation
* **Canonical Dish Imagery:** Automatically generated, perception-grounded visuals that reflect the "consensus reality" of how a dish is served, rather than idealized marketing imagery.
* **Structured Menu Knowledge:** Exportable, per-item descriptions (including price, ingredients, and dietary markers) for digital menus, menu boards, and websites.

---

## ⚙️ System Overview

Dishy operates as an agentic pipeline built on Gemini 3’s multimodal reasoning capabilities:

0. **Review Scraping**
   *Located in `core/review_scraping`*
   Scrapes raw user reviews (both text and images) to gather the initial unstructured dataset.

1. **Menu Listing & Embeddings**
   *Located in `core/menu_listing`*
   * **Multimodal Embedding:** Generates 128-dimensional embeddings for all images using the **Vertex AI Multimodal Embedding Model**.
   * **Menu Board Retrieval:** Identifies menu boards by calculating the cosine similarity between image embeddings and the text query below.:
      ```
      "A photo of a full restaurant menu showing all menu items and prices, with the entire menu visible in frame and little surrounding background, organized for customer ordering"
      ```
     It uses a date-backoff strategy to prioritize recent menus.
   * **Extraction:** Clusters the top retrieved images to handle diverse angles/pages and feeds them into **Gemini 3** to extract a structured JSON menu (names, prices, descriptions).

2. **Text Review Labeling & Aggregation**
   *Located in `core/text_review_labeling`*
   * **Review Association:** Associates each review with a specific menu item from the previous stage.
   * **Per-Menu Summarization:** Aggregates all relevant reviews for a single dish and uses **Gemini 3** to synthesize a "source of truth" summary. This includes **Objective Summary**, **Physical Appearance**, **Ingredients**, **Dietary Claims**, and **Review Discrepancies**.

3. **Restaurant Overview & Glossary**
   *Located in `core/restuarant_overview`*
   * **Collective Summarization:** Uses **Gemini 3** to synthesize a high-level summary of the most popular items based on review volume, grouping them by serving style (e.g., individual mains vs. shared plates).
   * **Curated Glossary:** Generates a dictionary of common romanized terms and cuisine-specific vocabulary, providing grounding definitions for users unfamiliar with the cuisine.

4. **Image Classification & Generation**
   *Located in `core/image_generating`*
   * **Semantic Search:** Calculates similarity between the **generated appearance description** (from Stage 2) and candidate images to find the photos that best match the *consensus visual description* of the dish.
   * **Collage Creation:** Selects the top 9 most representative images and creates a 3x3 collage to serve as the canonical visual reference.

5. **NanoBanana Integration**
   The final curated assets—structured menu data, synthesized text summaries, and visual collages—are fed into **NanoBanana** to generate high-fidelity canonical visual references and power the final presentation layer.

This process emphasizes **reasoning, synthesis, and verification**, making it impossible to solve with a single prompt or baseline RAG approach.

---

## 📝 Summary

Dishy reframes restaurant discovery as a **dish-level understanding problem**. By synthesizing unified visual and semantic representations from noisy user-generated content, it creates a new layer of structured, trustworthy menu intelligence—helping people decide what to eat without reading hundreds of reviews.

For any questions, please contact `ujinsong@stanford.edu`, `heejuyt@gmail.com`