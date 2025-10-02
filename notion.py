import os
import json
from notion_client import Client
from dotenv import load_dotenv
import openai
import numpy as np
import faiss
from rank_bm25 import BM25Okapi

# -----------------------
# Load environment variables
# -----------------------
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PAGE_ID = os.getenv("NOTION_PAGE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

DB_PATH = "db/resume_sections.json"
FAISS_INDEX_PATH = "db/resume_faiss.index"
EMBEDDINGS_PATH = "db/resume_embeddings.npy"

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)

# -----------------------
# Fetch Notion and create JSON
# -----------------------
def fetch_hierarchical_sections():
    """
    Fetch hierarchical sections from Notion page.
    Returns a nested dictionary according to heading_1, heading_2, heading_3, paragraphs, and bullets.
    """
    try:
        blocks = notion.blocks.children.list(PAGE_ID)["results"]
    except Exception as e:
        print("ERROR: Error fetching Notion blocks:", e)
        raise

    hierarchy = {}
    current_h1 = None
    current_h2 = None
    current_h3 = None

    for b in blocks:
        btype = b.get("type")
        if btype in ["heading_1", "heading_2", "heading_3"]:
            rich_texts = b.get(btype, {}).get("rich_text", [])
            heading_text = rich_texts[0].get("plain_text", "").strip() if rich_texts else None
            if not heading_text:
                continue
            if btype == "heading_1":
                current_h1 = heading_text
                hierarchy[current_h1] = {}
                current_h2 = current_h3 = None
            elif btype == "heading_2":
                if current_h1 is None: continue
                current_h2 = heading_text
                hierarchy[current_h1][current_h2] = {}
                current_h3 = None
            elif btype == "heading_3":
                if current_h1 is None or current_h2 is None: continue
                current_h3 = heading_text
                hierarchy[current_h1][current_h2][current_h3] = []

        elif btype == "paragraph":
            rich_texts = b.get("paragraph", {}).get("rich_text", [])
            text = " ".join([t.get("plain_text", "") for t in rich_texts]).strip()
            if not text: continue
            if current_h1 and current_h2 and current_h3:
                hierarchy[current_h1][current_h2][current_h3].append(text)
            elif current_h1 and current_h2:
                hierarchy[current_h1][current_h2].setdefault("_content", []).append(text)
            elif current_h1:
                hierarchy[current_h1].setdefault("_content", []).append(text)

        elif btype == "bulleted_list_item":
            rich_texts = b.get("bulleted_list_item", {}).get("rich_text", [])
            text = " ".join([t.get("plain_text", "") for t in rich_texts]).strip()
            if not text: continue
            if current_h1 and current_h2 and current_h3:
                hierarchy[current_h1][current_h2][current_h3].append(f"• {text}")
            elif current_h1 and current_h2:
                hierarchy[current_h1][current_h2].setdefault("_content", []).append(f"• {text}")
            elif current_h1:
                hierarchy[current_h1].setdefault("_content", []).append(f"• {text}")

    # Convert lists of paragraphs into single strings
    def join_paragraphs(d):
        for k, v in d.items():
            if isinstance(v, dict):
                join_paragraphs(v)
            elif isinstance(v, list):
                d[k] = " ".join(v)

    join_paragraphs(hierarchy)
    return hierarchy

# -----------------------
# Save JSON + build FAISS + BM25
# -----------------------
def save_json_and_build_index():
    hierarchy = fetch_hierarchical_sections()
    os.makedirs("db", exist_ok=True)

    # Save JSON
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)

    # Flatten JSON
    flat_resume = []
    def flatten_json(json_data, parent_keys=[]):
        for k, v in json_data.items():
            current_path = parent_keys + [k]
            if isinstance(v, dict):
                flatten_json(v, current_path)
            else:
                flat_resume.append({"title": " > ".join(current_path), "content": v})
    flatten_json(hierarchy)

    corpus_texts = [item["content"] for item in flat_resume]

    # -----------------------
    # OpenAI Embeddings
    # -----------------------
    embeddings = []
    for text in corpus_texts:
        try:
            resp = openai.embeddings.create(
               model="text-embedding-3-large",
               input=text
)
            embeddings.append(resp.data[0].embedding)
        except Exception as e:
            print(f"WARNING: OpenAI embedding failed: {e}, will fallback to BM25.")
            embeddings = None
            break

    # -----------------------
    # FAISS index if embeddings exist
    # -----------------------
    if embeddings:
        embeddings = np.array(embeddings, dtype="float32")
        np.save(EMBEDDINGS_PATH, embeddings)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)
        faiss.write_index(index, FAISS_INDEX_PATH)
        print("SUCCESS: FAISS index and OpenAI embeddings saved.")

    # -----------------------
    # BM25 fallback
    # -----------------------
    tokenized_corpus = [text.split() for text in corpus_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    with open("db/bm25.pkl", "wb") as f:
        import pickle
        pickle.dump({"bm25": bm25, "flat_resume": flat_resume}, f)
    print("SUCCESS: BM25 index saved as fallback.")

if __name__ == "__main__":
    save_json_and_build_index()

