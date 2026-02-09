import warnings
# Suppress specific Google/Vertex AI warnings globally
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from menu_listing.constants import SUPPORTED_DIMS, GCP_PROJECT_ID, GCP_LOCATION, PROJECT_ROOT
import vertexai
from vertexai.vision_models import MultiModalEmbeddingModel
import json
import os
import tqdm
from utils.helpers import get_curr_time

def generate_and_save_vectors(query_text: str):
    # Initialize Vertex AI
    vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    mm_embedding_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")

    output_file = PROJECT_ROOT / "core" / "menu_listing" / "query_vectors.json"
    with open(output_file, "r") as f:
        entries = json.load(f)

    print(f"[{get_curr_time()}] Processing Query Text:\n{query_text}")
    
    new_entry = {"text": query_text}
    for dim in tqdm.tqdm(SUPPORTED_DIMS):
        try:
            embedding_response = mm_embedding_model.get_embeddings(
                contextual_text=query_text,
                dimension=dim
            )
            new_entry[dim] = embedding_response.text_embedding
        except Exception as e:
            print(f"[{get_curr_time()}] Error generating embedding for dim={dim}: {e}")

    entries.append(new_entry)
    with open(output_file, 'w') as f:
        json.dump(entries, f, indent=2)
    
    print(f"[{get_curr_time()}] Saved query vector to {output_file}")
    return new_entry
    

if __name__ == "__main__":
    pass
