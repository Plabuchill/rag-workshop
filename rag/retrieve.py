"""ค้นคืน chunk ที่เกี่ยวข้องกับคำถาม (เวิร์กช็อป 2 และ 4) ทำงานในเครื่องทั้งหมด ไม่เรียก API

python -m rag.retrieve "คำถาม" -k 4 [--method tfidf|hybrid] [--include-superseded] [--json]
"""
import argparse
import json

import numpy as np
from pythainlp.tokenize import word_tokenize
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from rag.chunk import chunk_docs

METHODS = ("tfidf", "hybrid")
# 0.2–0.4 ให้ผล dev เท่ากัน เลือกค่ากลาง ที่ 0.5 BM25 ดึง "ทดลองงาน" (HR-05) ขึ้นมาแทนลาพักร้อนใน Q01
BM25_WEIGHT = 0.3

# คำพ้องสำหรับขยายคำค้น (hybrid) สร้างจากคำถามชุด dev ที่ผลอันดับ 1 พลาดเท่านั้น (ห้ามใช้ชุด test)
# คีย์คือคำที่ผู้ใช้พิมพ์ ค่าคือคำที่เอกสารใช้
SYNONYMS = {
    "อีวี": "รถยนต์ไฟฟ้า",  # Q35
    "ev": "รถยนต์ไฟฟ้า",
    "เสียบชาร์จ": "จุดชาร์จ",  # Q35
    "พาสเวิร์ด": "รหัสผ่าน",  # Q24
}


def index_text(c: dict) -> str:
    return f"{c['title']}\n{c['section']}\n{c['text']}"


def tokenize(text: str) -> list[str]:
    """ตัดคำภาษาไทยด้วย pythainlp (newmm) ทิ้งช่องว่างและเครื่องหมาย"""
    return [t.lower() for t in word_tokenize(text, engine="newmm") if any(ch.isalnum() for ch in t)]


def expand_query(query: str) -> str:
    q = query.lower()
    return " ".join([query, *(v for k, v in SYNONYMS.items() if k in q)])


def scale(x: np.ndarray) -> np.ndarray:
    """หารด้วยค่าสูงสุดให้อยู่ในช่วง 0–1 เพื่อนำคะแนนสองวิธีมารวมกันได้"""
    top = x.max()
    return x / top if top > 0 else x


class Retriever:
    def __init__(self, chunks: list[dict] | None = None, method: str = "tfidf"):
        """method="tfidf": TF-IDF ระดับตัวอักษร (W2) · method="hybrid": TF-IDF + BM25 + คำพ้อง (W4)"""
        if method not in METHODS:
            raise ValueError(f"method ต้องเป็นหนึ่งใน {METHODS}")
        self.method = method
        self.chunks = chunk_docs() if chunks is None else chunks
        texts = [index_text(c) for c in self.chunks]
        # ภาษาไทยไม่เว้นวรรคระหว่างคำ จึงใช้ n-gram ระดับตัวอักษรแทนการตัดคำ
        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(texts)
        if method == "hybrid":
            self.bm25 = BM25Okapi([tokenize(t) for t in texts])

    def scores(self, query: str) -> np.ndarray:
        if self.method == "hybrid":
            query = expand_query(query)
        # TfidfVectorizer ทำ L2 normalize แล้ว dot product จึงเท่ากับ cosine similarity
        tfidf = linear_kernel(self.vectorizer.transform([query]), self.matrix).ravel()
        if self.method == "tfidf":
            return tfidf
        bm25 = np.asarray(self.bm25.get_scores(tokenize(query)))
        return (1 - BM25_WEIGHT) * scale(tfidf) + BM25_WEIGHT * scale(bm25)

    def search(self, query: str, k: int = 4, include_superseded: bool = True) -> list[dict]:
        """คืน chunk k อันที่คะแนนสูงสุด เรียงจากมากไปน้อย แต่ละอันเพิ่มช่อง "score" """
        scores = self.scores(query)
        results = []
        for i in np.argsort(-scores, kind="stable"):
            c = self.chunks[i]
            if not include_superseded and c["status"] != "active":
                continue
            results.append({**c, "score": float(scores[i])})
            if len(results) == k:
                break
        return results


def main():
    ap = argparse.ArgumentParser(description="ค้นคืน chunk จากคำถาม")
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=4)
    ap.add_argument("--method", default="tfidf", choices=["tfidf", "hybrid"])
    ap.add_argument("--include-superseded", action="store_true")
    ap.add_argument("--json", action="store_true", help="พิมพ์ผลเป็น JSON")
    a = ap.parse_args()
    res = Retriever(method=a.method).search(a.query, a.k, a.include_superseded)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    for r in res:
        print(f"[{r['score']:.3f}] {r['chunk_id']} · {r['title']} › {r['section']} ({r['status']}, {r['effective_date']})")
        print("    " + r["text"].replace("\n", "\n    "))


if __name__ == "__main__":
    main()
