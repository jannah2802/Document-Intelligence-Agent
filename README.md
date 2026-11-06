# Document-Intelligence-Agent
This repo is to build a document intelligence agent that can process financial documents such as invoices or receipt, extract structured data, and produce a short summary.

## Run the API

Install dependencies and start the development server:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Upload a PDF, JPEG, or PNG using a multipart form field named `file`:

```bash
curl -F "file=@invoice.pdf" http://localhost:8000/documents
```

Uploads are stored in `data/documents` by default. Set `DOCUMENT_STORAGE_DIR` to use another directory. The endpoint returns HTTP `202` with a generated document ID and `processing` status. The background agent extracts text, sends it to an OpenAI model for structured invoice extraction, validates the result, and generates a concise summary. Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` (defaults to `gpt-4o-mini`) before uploading.

Install the Tesseract system executable (for example, `sudo apt install tesseract-ocr` on Ubuntu). Final results are written to `data/results/<document_id>.json` by default; set `DOCUMENT_RESULTS_DIR` to change this location. Poll `GET /documents/<document_id>` to see the current step (`queued`, `extracting_text`, `extracting_fields`, `validating`, `generating_summary`, or `completed`) and retrieve the final result. Processing errors return a `failed` status with a generic message; details are logged by the API.
