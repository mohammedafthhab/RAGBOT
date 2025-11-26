import os, sys
#sys.stderr = open(os.devnull, "w")
import re
import subprocess
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import numpy as np
import pdfplumber, requests
from PIL import Image
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import faiss

from collections import deque

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# ------------------ MONGODB SETUP ------------------
from pymongo import MongoClient
import time

MONGO_URI = ""

client = MongoClient(MONGO_URI)

db = client["seed_chatbot"]
chat_collection = db["chat_history"]


def save_chat(role, message, user="guest"):
    chat_collection.insert_one({
        "user": user,
        "role": role,
        "message": message,
        "timestamp": time.time()
    })


def get_all_chats():
    chats = chat_collection.find().sort("timestamp", 1)
    history = []
    for c in chats:
        history.append({
            "role": c["role"],
            "message": c["message"],
            "time": c["timestamp"]
        })
    return history


# ------------------ CHATBOT INITIALIZATION ------------------

chat_history = deque(maxlen=8)

app = Flask(__name__)
CORS(app)

DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)


# ------------------ WEB SCRAPING ------------------
def scrape_web_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "footer", "header", "form"]):
            tag.decompose()

        text = " ".join(soup.stripped_strings)
        return text[:100000]
    except:
        return ""


# ------------------ TEXT EXTRACTION ------------------
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""

        for page in reader.pages:
            txt = page.extract_text()
            if txt and isinstance(txt, str):
                text += txt + "\n"

        return text

    except Exception as e:
        print("PDF extraction error:", e)
        return ""


# ------------------ LOAD DATA ------------------
URLS = [
    "https://en.wikipedia.org/wiki/Artificial_intelligence"
]

import json, stat

def load_all_data(folder):
    """
    Legacy loader kept for compatibility but not used by the new cache-first logic.
    """
    corpus = []
    sources = []

    # --- Load PDFs ---
    for file in os.listdir(folder):
        path = os.path.join(folder, file)

        if file.lower().endswith(".pdf"):
            text = extract_text_from_pdf(path)
        else:
            continue

        # Safe sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for chunk in sentences:
            if isinstance(chunk, str) and len(chunk.strip()) > 20:
                corpus.append(chunk.strip())
                sources.append(file)

    # --- Load URLs ---
    for url in URLS:
        text = scrape_web_content(url)

        sentences = re.split(r'(?<=[.!?])\s+', text)

        for chunk in sentences:
            if isinstance(chunk, str) and len(chunk.strip()) > 20:
                corpus.append(chunk.strip())
                sources.append(url)

    return corpus, sources


# ------------------ FAISS & CACHE SYSTEM (ADDED/ MODIFIED) ------------------

# cache paths and helpers
CACHE_FOLDER = "seed_cache"
os.makedirs(CACHE_FOLDER, exist_ok=True)

CHUNK_FILE = f"{CACHE_FOLDER}/chunks.json"    # stores list of {text, source}
META_FILE = f"{CACHE_FOLDER}/meta.json"      # stores processed file metadata
FAISS_FILE = f"{CACHE_FOLDER}/index.faiss"   # faiss index
URL_CACHE_FILE = f"{CACHE_FOLDER}/urls_cache.json"  # cached scraped url texts

def save_cache(chunks, file_meta, index, url_cache):
    """
    Save chunks (list of dicts: {'text':..,'source':..}),
    file_meta: dict filename -> {'size':..,'mtime':..}
    index: faiss index to write.
    url_cache: dict url->text
    """
    with open(CHUNK_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    with open(META_FILE, "w") as f:
        json.dump(file_meta, f)

    with open(URL_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(url_cache, f, ensure_ascii=False)

    # write faiss index
    try:
        faiss.write_index(index, FAISS_FILE)
    except Exception as e:
        print("Failed to write FAISS index:", e)


def load_cache():
    if not (os.path.exists(CHUNK_FILE) and os.path.exists(META_FILE) and os.path.exists(FAISS_FILE) and os.path.exists(URL_CACHE_FILE)):
        return None, None, None, None

    with open(CHUNK_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    with open(META_FILE, "r") as f:
        meta = json.load(f)

    with open(URL_CACHE_FILE, "r", encoding="utf-8") as f:
        url_cache = json.load(f)

    try:
        index = faiss.read_index(FAISS_FILE)
    except Exception as e:
        print("Failed to read FAISS index:", e)
        index = None

    return chunks, meta, index, url_cache


def get_pdf_list():
    return sorted([f for f in os.listdir(DATA_FOLDER) if f.lower().endswith(".pdf")])


def file_info(path):
    st = os.stat(path)
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def normalize_text(t):
    # basic normalization for deduplication: lowercase, strip, collapse spaces
    if not isinstance(t, str):
        return ""
    t = t.replace("\n", " ").replace("\t", " ")
    t = re.sub(r"\s{2,}", " ", t)
    t = t.strip().lower()
    return t


# --- SAFE TEXT: prevents SentenceTransformer tokenizer crashes
def safe_text(t):
    """Return clean valid UTF-8 string or None."""
    if not isinstance(t, str):
        return None
    t = t.strip()
    if len(t) < 5:
        return None
    # remove control chars
    t = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", t)
    # collapse multiple spaces
    t = re.sub(r"\s{2,}", " ", t).strip()
    try:
        t.encode("utf-8")
    except:
        return None
    return t


# create model + index helper (FLAT L2 only — stable on macOS)
def create_faiss_index_from_texts(texts):
    model_local = SentenceTransformer("all-MiniLM-L6-v2")
    # ensure texts is a list of str
    safe_texts = [t for t in texts if isinstance(t, str) and len(t) > 0]
    embeddings = model_local.encode(safe_texts, show_progress_bar=False)
    dim = embeddings.shape[1]

    # Safe FAISS on macOS (NO HNSW)
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))

    return model_local, index


# main improved loading logic (incremental + url caching + dedup)
print("🔍 Checking cache...")

cached_chunks, cached_meta, cached_index, cached_url_cache = load_cache()
current_files = get_pdf_list()

# Initialize model early (SentenceTransformer loads only once)
model = SentenceTransformer("all-MiniLM-L6-v2")

# We'll maintain clean_chunks as list of dicts {'text':..., 'source':...}
clean_chunks = []
url_cache = {}
file_meta = {}

# Attempt to use cached data if valid
if cached_chunks is not None and cached_meta is not None and cached_index is not None and cached_url_cache is not None:
    # Determine changed / new / removed files using metadata (size + mtime)
    print("🔁 Cache found. Checking for changed or new PDFs...")

    # load cached metadata
    file_meta_cached = cached_meta.get("files", {})

    # Build a set of files to process (new or changed)
    to_process = []
    current_meta = {}
    for fname in current_files:
        path = os.path.join(DATA_FOLDER, fname)
        info = file_info(path)
        current_meta[fname] = info
        cached_info = file_meta_cached.get(fname)
        if cached_info is None:
            to_process.append(fname)  # new file
        else:
            if cached_info.get("size") != info["size"] or cached_info.get("mtime") != info["mtime"]:
                to_process.append(fname)  # changed file

    # Files that were in cache but removed from folder will remain in the index/chunks.
    # (Optionally you can remove them — not done here to avoid complex reindexing.)
    if len(to_process) == 0:
        # nothing changed -> load full cache
        print("✅ No changes detected in PDFs. Using cached chunks and index.")
        clean_chunks = cached_chunks
        file_meta = file_meta_cached
        index = cached_index
        url_cache = cached_url_cache
    else:
        print(f"🆕 Detected {len(to_process)} new/changed file(s): {to_process}")
        # Start from cached content
        existing_texts = [c["text"] for c in cached_chunks]
        existing_norms = set(normalize_text(t) for t in existing_texts)

        clean_chunks = cached_chunks.copy()
        index = cached_index
        url_cache = cached_url_cache.copy()
        file_meta = file_meta_cached.copy()

        for fname in to_process:
            print("➡ Processing:", fname)
            path = os.path.join(DATA_FOLDER, fname)
            text = extract_text_from_pdf(path)
            sentences = re.split(r'(?<=[.!?])\s+', text)

            new_texts = []
            for s in sentences:
                s_clean = s.replace("\n", " ").replace("\t", " ")
                s_clean = re.sub(r"\s{2,}", " ", s_clean).strip()
                if 30 < len(s_clean) < 500:
                    norm = normalize_text(s_clean)
                    if norm in existing_norms:
                        continue
                    s2 = safe_text(s_clean)
                    if not s2:
                        continue
                    existing_norms.add(norm)
                    new_texts.append(s2)
                    clean_chunks.append({"text": s2, "source": fname})

            if new_texts:
                # embed and add to FAISS
                try:
                    new_embeddings = model.encode(new_texts, show_progress_bar=False)
                    index.add(np.array(new_embeddings))
                except Exception as e:
                    print("Embedding/add to FAISS failed for", fname, "error:", e)

            # update file_meta entry
            file_meta[fname] = file_info(path)

        # Save updated cache
        save_cache(clean_chunks, {"files": file_meta}, index, url_cache)
        print("✅ Cache updated after processing new/changed PDFs.")

else:
    # No cache: process everything
    print("⚠ No cache found. Processing all PDFs and URLs...")

    clean_chunks = []
    file_meta = {}

    # Process PDFs
    for fname in current_files:
        print("➡ Processing PDF:", fname)
        path = os.path.join(DATA_FOLDER, fname)
        text = extract_text_from_pdf(path)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for s in sentences:
            s_clean = s.replace("\n", " ").replace("\t", " ")
            s_clean = re.sub(r"\s{2,}", " ", s_clean).strip()
            if 30 < len(s_clean) < 500:
                s2 = safe_text(s_clean)
                if s2:
                    clean_chunks.append({"text": s2, "source": fname})

        file_meta[fname] = file_info(path)

    # Process URLs with caching (scrape each URL once)
    url_cache = {}
    for url in URLS:
        print("➡ Scraping URL:", url)
        text = scrape_web_content(url)
        url_cache[url] = text
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for s in sentences:
            s_clean = s.replace("\n", " ").replace("\t", " ")
            s_clean = re.sub(r"\s{2,}", " ", s_clean).strip()
            if 30 < len(s_clean) < 500:
                s2 = safe_text(s_clean)
                if s2:
                    clean_chunks.append({"text": s2, "source": url})

    # Deduplicate chunks (normalized)
    seen = set()
    deduped = []
    for item in clean_chunks:
        norm = normalize_text(item["text"])
        if norm in seen:
            continue
        seen.add(norm)
        deduped.append(item)
    clean_chunks = deduped

    # Create FAISS index from scratch
    texts = [c["text"] for c in clean_chunks]
    if len(texts) == 0:
        # empty dataset safety
        model_local = SentenceTransformer("all-MiniLM-L6-v2")
        index = faiss.IndexFlatL2(1)
    else:
        model_local, index = create_faiss_index_from_texts(texts)
        # ensure model variable references the same SentenceTransformer loaded earlier
        model = model_local

    # Save everything
    save_cache(clean_chunks, {"files": file_meta}, index, url_cache)
    print("✅ Full cache created and FAISS index saved.")


# Post-load: build parallel sources list for compatibility with existing chat flow
sources = [c["source"] for c in clean_chunks]

print("📌 Total chunks loaded:", len(clean_chunks))


# ------------------ LLM CALL ------------------
def ask_llm(question, context):
    prompt = f"""You are StudyMentor, a friendly AI & ML guide helping users understand concepts, algorithms, math, and workflows. Do NOT mention this line in answers. Never say “according to” or similar words. Always refer to source material as “background material” and cite it naturally in this format: [Source: <name>].

CRITICAL RULE: Answer ONLY using facts from the Background Material {context} below. NEVER use outside information.

If the user ends with words like “thanks” or “thank you,” reply warmly and end politely.  
If the user writes “ok,” “sure,” “no problem,” or similar, reply with a warm short sentence and end politely.

=== IDENTITY & GREETING ===
First interaction:
- If the user greets (hi/hello/hey): Respond warmly like their silent study partner. No citations here.
- If the user asks a question directly: Answer immediately without greeting.

After first message:
- Do NOT repeat your introduction.
- Only mention “silent study partner” if asked or if reassuring naturally.
- Always respond like a supportive friend who understands AI & ML.

=== TONE ===
- Warm, simple, helpful.
- Explain complex topics clearly.
- Not overly formal.
- Never say “from the files” or “from uploaded documents.”

=== FORMATTING RULES (MANDATORY) ===
✓ Use clear formatting with spacing  
✓ Use numbered steps:

1. First step  
   - Short explanation  
   - Small summary line  

2. Second step  
   - Short explanation  
   - Small summary line  

✓ Keep structure clean  
✓ Minimal bold  
✓ Cite sources ONLY when using background material (e.g., [Source: Deep Learning Notes])

=== ANSWERING RULES ===

For general study questions:  
- Give 3–5 steps explaining the concept  
- If present in background material, include:  
  • Definitions  
  • Use cases  
  • Mathematical intuition  
  • Examples

For specific questions:  
- Answer ONLY using background material  
- If info is missing, politely stop without guessing  
- DO NOT create new facts  
- Cite every factual line that comes from background material in the proper format

For harmful or unethical requests (e.g., bypassing systems, model exploitation, cheating):
- Politely refuse.

=== BACKGROUND MATERIAL ===
{context}

=== USER MESSAGE ===
{question}

Now respond in a clean, line-by-line structured format following all rules above."""
    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=prompt.encode(),
        capture_output=True
    )
    return result.stdout.decode().strip()


# ------------------ GESTURE RECOGNITION ------------------

import json, threading
from queue import Queue, Empty
import cv2
import mediapipe as mp
import pickle

gesture_events = Queue()
gesture_stop_event = threading.Event()
gesture_running = False

SEND_GESTURE = "Good"
UNDO = "undo"
CLEAR = "clear"
CLOSE = "bad"
START_DELAY = 1
GESTURE_WINDOW = 1

with open("models/gesture_model.pkl", "rb") as f:
    gesture_model = pickle.load(f)
with open("models/label_encoder.pkl", "rb") as f:
    gesture_le = pickle.load(f)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)


def normalize_landmarks(landmarks):
    arr = np.array(landmarks).reshape(-1, 3)
    wrist = arr[0]
    arr -= wrist
    m = np.max(np.abs(arr))
    if m != 0:
        arr /= m
    return arr.flatten().tolist()


def gesture_loop():
    time.sleep(START_DELAY)
    gesture_events.put({"type": "status", "value": "ready"})

    cap = cv2.VideoCapture(0)
    sentence = []
    last_pred = None
    collecting = False
    t0 = 0

    while not gesture_stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            continue

        imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(imgRGB)

        current = None
        if result.multi_hand_landmarks:
            hLms = result.multi_hand_landmarks[0]
            lm = [[p.x, p.y, p.z] for p in hLms.landmark]
            feats = np.array([normalize_landmarks(lm)], dtype=np.float32)
            idx = gesture_model.predict(feats)[0]
            current = gesture_le.inverse_transform([idx])[0]

        if current is None:
            last_pred = None
            collecting = False
            continue

        if current != last_pred:
            last_pred = current
            t0 = time.time()
            collecting = True

        if collecting and time.time() - t0 >= GESTURE_WINDOW:
            collecting = False

            if current.lower() == SEND_GESTURE.lower():
                final = " ".join(sentence).strip()
                gesture_events.put({"type": "send", "value": final})
                sentence = []

            elif current.lower() == UNDO.lower():
                if sentence:
                    removed = sentence.pop()
                    gesture_events.put({"type": "undo", "value": removed})

            elif current.lower() == CLEAR.lower():
                sentence = []
                gesture_events.put({"type": "clear", "value": ""})

            elif current.lower() == CLOSE.lower():
                gesture_stop_event.set()
                gesture_events.put({"type": "close"})
                break

            else:
                sentence.append(current)
                gesture_events.put({"type": "sentence", "value": " ".join(sentence)})

    cap.release()
    gesture_events.put({"type": "status", "value": "stopped"})


def format_sse(obj):
    return "data: " + json.dumps(obj) + "\n\n"


@app.route("/gesture/start", methods=["POST"])
def gesture_start():
    global gesture_running
    if gesture_running:
        return jsonify({"status": "already_running"})
    gesture_stop_event.clear()

    t = threading.Thread(target=gesture_loop, daemon=True)
    t.start()
    gesture_running = True
    return jsonify({"status": "started"})


@app.route("/gesture/stop", methods=["POST"])
def gesture_stop():
    global gesture_running
    gesture_stop_event.set()
    gesture_running = False
    return jsonify({"status": "stopped"})


@app.route("/gesture/stream")
def gesture_stream():
    def event_stream():
        yield format_sse({"type": "status", "value": "connecting"})
        while not gesture_stop_event.is_set():
            try:
                evt = gesture_events.get(timeout=0.5)
                yield format_sse(evt)
            except Empty:
                yield ": keep-alive\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


# ------------------ CHAT ENDPOINTS ------------------

@app.route("/")
def home():
    return "✅ StudyMentor backend is running successfully!"


@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    # Save user msg
    save_chat("user", query)

    # RAG search
    q_embed = model.encode([query])
    D, I = index.search(q_embed, 3)
    context_chunks = [clean_chunks[i]["text"] for i in I[0]]
    context_sources = [clean_chunks[i]["source"] for i in I[0]]

    context_text = "\n\n".join(
        [f"[Source: {context_sources[i]}]\n{context_chunks[i]}" for i in range(len(context_chunks))]
    )

    # LLM reply
    answer = ask_llm(query, context_text)

    # Save bot reply
    save_chat("bot", answer)

    return jsonify({"answer": answer})


@app.route("/history", methods=["GET"])
def history_api():
    return jsonify([])  # Always return empty chat history

@app.route("/full-history", methods=["GET"])
def full_history_api():
    return jsonify(get_all_chats())   # return REAL history



if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
