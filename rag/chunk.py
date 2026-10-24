"""แบ่งเอกสารเป็น chunk พร้อม metadata (เวิร์กช็อป 1)

แต่ละ chunk เป็น dict ที่มีอย่างน้อย:
chunk_id ("<doc_id>#<ลำดับ>"), doc_id, title, section, status, effective_date, text
"""
from rag.ingest import load_docs

MAX_CHARS = 600
META_KEYS = ("doc_id", "title", "department", "version", "effective_date", "status", "path")


def split_sections(body: str, default: str) -> list[tuple[str, list[str]]]:
    """คืน [(ชื่อหัวข้อ, บรรทัดเนื้อหา)] ตามหัวข้อ ## ข้ามบรรทัด # ชื่อเรื่อง"""
    sections, name, lines = [], default, []
    for line in body.splitlines():
        if line.startswith("## "):
            if any(l.strip() for l in lines):
                sections.append((name, lines))
            name, lines = line[3:].strip(), []
        elif not line.startswith("# "):
            lines.append(line)
    if any(l.strip() for l in lines):
        sections.append((name, lines))
    return sections


def pack(section: str, lines: list[str], max_chars: int) -> list[str]:
    """รวมบรรทัดเป็นก้อนละไม่เกิน max_chars ทุกก้อนขึ้นต้นด้วยชื่อหัวข้อ"""
    head = section + "\n"
    room = max_chars - len(head)
    pieces = []
    for line in (l.strip() for l in lines):
        if not line:
            continue
        # บรรทัดเดียวที่ยาวเกินจะถูกตัดตามจำนวนตัวอักษร
        pieces += [line[i:i + room] for i in range(0, len(line), room)]
    texts, cur = [], []
    for p in pieces:
        if cur and len(head + "\n".join(cur + [p])) > max_chars:
            texts.append(head + "\n".join(cur))
            cur = []
        cur.append(p)
    if cur:
        texts.append(head + "\n".join(cur))
    return texts


def chunk_docs(docs: list[dict] | None = None, max_chars: int = MAX_CHARS) -> list[dict]:
    docs = load_docs() if docs is None else docs
    chunks = []
    for d in docs:
        meta = {k: d.get(k, "") for k in META_KEYS}
        n = 0
        for section, lines in split_sections(d["body"], d.get("title", "")):
            for text in pack(section, lines, max_chars):
                n += 1
                chunks.append({**meta, "chunk_id": f"{d['doc_id']}#{n}", "section": section, "text": text})
    return chunks


if __name__ == "__main__":
    cs = chunk_docs()
    print(len(cs), "chunks · ยาวสุด", max(len(c["text"]) for c in cs), "ตัวอักษร")
