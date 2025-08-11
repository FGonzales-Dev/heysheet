import os, pickle
from pathlib import Path
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
from sentence_transformers import SentenceTransformer
import faiss
from groq import Groq
from django.conf import settings

BASE_DIR = Path(settings.BASE_DIR)  # points to backend/
INDEX_PATH = str(BASE_DIR / "sheet_index.faiss")
META_PATH  = str(BASE_DIR / "sheet_meta.pkl")

def fetch_sheet() -> pd.DataFrame:
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=creds)
    values = service.spreadsheets().values().get(
        spreadsheetId=os.environ["SPREADSHEET_ID"],
        range=os.getenv("SHEETS_RANGE", "Business Hours!A1:Z"),
    ).execute().get("values", [])

    if not values:
        return pd.DataFrame()

    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers[:len(rows[0])])
    df.reset_index(drop=True, inplace=True)
    df["__row_id"] = df.index + 2  # header is row 1
    return df

def build_index(df: pd.DataFrame):
    cols = [c for c in df.columns if c != "__row_id"]
    docs, meta = [], []
    for _, r in df.iterrows():
        text = " | ".join(f"{c}: {str(r[c])}" for c in cols)
        docs.append(text)
        meta.append({"row": int(r["__row_id"]), "text": text})

    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embs = embedder.encode(docs, convert_to_numpy=True, normalize_embeddings=True)

    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)

    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump({"meta": meta}, f)

def sync_sheet() -> int:
    df = fetch_sheet()
    if df.empty:
        raise RuntimeError("Sheet empty or inaccessible.")
    build_index(df)
    return len(df)

class QAEngine:
    def __init__(self):
        if not (os.path.exists(INDEX_PATH) and os.path.exists(META_PATH)):
            raise RuntimeError("Index not built. Call /api/notes/sync first.")
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "rb") as f:
            self.meta = pickle.load(f)["meta"]
        self.llm = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def retrieve(self, question: str, k: int = 6):
        qv = self.embedder.encode([question], convert_to_numpy=True, normalize_embeddings=True)
        D, I = self.index.search(qv, k)
        out = []
        for i, score in zip(I[0], D[0]):
            if i == -1: continue
            m = self.meta[i]
            out.append({"row": m["row"], "text": m["text"], "score": float(score)})
        return out

    def ask(self, question: str):
        ctxs = self.retrieve(question, k=6)
        ctx_block = "\n\n".join(f"[Row {c['row']}] {c['text']}" for c in ctxs)
        system = ("Answer using ONLY the spreadsheet context. "
                  "If unknown, say you don't know and reference the closest rows.")
        user = f"Context:\n{ctx_block}\n\nQuestion: {question}\nProvide a concise answer with row refs."
        resp = self.llm.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0.2,
        )
        return resp.choices[0].message.content, ctxs
