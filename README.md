# MOSIP OCR Hackathon

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2-61DAFB.svg)](https://react.dev/)

> **Intelligent Document Processing System** — AI-powered OCR with real-time verification for identity documents.

## Overview

Production-ready document processing system combining **TrOCR**, **EasyOCR**, and **Phi-3 LLM** for high-accuracy text extraction and intelligent verification. Built for MOSIP ecosystem with >95% accuracy on printed forms.

### Key Features
- **Multi-model OCR**: TrOCR (recognition) + EasyOCR (detection) + Phi-3 (parsing)
- **Smart Verification**: Fuzzy matching with confidence scoring (Match/Partial/Mismatch)
- **Modern UI**: Drag-drop upload, real-time progress, interactive field editing
- **Production Ready**: FastAPI backend, React 19 frontend, RESTful API

## Quick Start

### Prerequisites
- Python 3.8+, Node.js 18+, [Ollama](https://ollama.ai/download)

### Installation

```bash
# Clone repository
git clone https://github.com/your-username/MOSIP_OCR_Hackathon.git
cd MOSIP_OCR_Hackathon

# Backend setup
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install fastapi uvicorn python-multipart transformers torch pillow easyocr opencv-python ollama

# Frontend setup
cd ../frontend
npm install

# Setup Phi-3
ollama serve  # Terminal 1
ollama pull phi3  # Terminal 2
```

### Run Application

```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: Backend (http://127.0.0.1:8000)
cd backend
uvicorn app:app --reload

# Terminal 3: Frontend (http://localhost:5173)
cd frontend
npm run dev
```

## API Reference

### `POST /extract`
Extract structured data from document image.

**Request**: `multipart/form-data` with `file` (image)

**Response**:
```json
{
  "status": "success",
  "extracted_data": {
    "Name": "John Doe",
    "Age": "29",
    "Email": "john@example.com"
  }
}
```

### `POST /verify`
Verify single field with confidence scoring.

```json
{
  "field_name": "Name",
  "extracted_text": "John Doe",
  "user_input": "John Due"
}
```

**Response**: `{"score": 88.89, "status": "PARTIAL_MATCH"}`

### `POST /verify-full`
Bulk verification for entire form.

**Docs**: Auto-generated at `http://127.0.0.1:8000/docs`

## Project Structure

```
├── backend/
│   ├── app.py              # API endpoints
│   ├── ocr_engine.py       # OCR pipeline (TrOCR + EasyOCR + Phi-3)
│   └── verifier.py         # Fuzzy matching logic
├── frontend/
│   └── src/App.jsx         # React UI with verification modal
└── test_samples/           # Sample documents
```

## Configuration

**Backend CORS** (`app.py`):
```python
allow_origins=["*"]  # Change in production
```

**Enable GPU** (`ocr_engine.py`):
```python
self.detector = easyocr.Reader(['en'], gpu=True)
```

**API Endpoint** (`frontend/src/App.jsx`):
```javascript
axios.post("http://YOUR_API_URL:8000/extract", ...)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Ollama connection refused | Run `ollama serve` |
| No text detected | Use 300+ DPI images, adjust `text_threshold=0.3` |
| Model download failed | Manually run `ollama pull phi3` |
| Slow processing | Enable GPU or reduce image size |

## License

MIT License — See [LICENSE](LICENSE) for details.
