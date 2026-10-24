# RAG Workshop · Claude Code + GitHub (ไม่ใช้ API credit)

ระบบถามตอบเอกสารบริษัทสมมติ "นาวา ดิจิทัล" สร้างด้วย Claude Code
การค้นคืนทำงานในเครื่องด้วย Python ส่วนการเขียนคำตอบทำโดย Claude Code ผ่าน skill `/ask`

```bash
pip install -r requirements.txt
pytest -q
python -m rag.retrieve "เบิกค่าทำฟันได้เท่าไร" -k 4
```

ใน Claude Code: `/ask ทำงานจากที่บ้านได้กี่วัน` · `/ask-eval dev 10`

**นาวา RAG Workbench** (เปิดดูเอกสาร ลองแบ่ง chunk ค้นคืนแบบ tfidf/hybrid และวัดผล dev บนเว็บ): https://plabuchill.github.io/rag-workshop/

ข้อมูลทั้งหมดเป็นของสมมติ
