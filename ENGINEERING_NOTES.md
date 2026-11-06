# Engineering Notes

## Project Goal

The goal is to process financial documents such as invoices and receipts, extract structured data, and produce a short summary. The repository implements an upload API and an agent pipeline for text extraction, structured invoice extraction, validation, and summary generation.

## Architecture Decisions

The implemented API is in `api/main.py`. `POST /documents` accepts a multipart `file` upload, allows PDF, JPEG, and PNG, checks the declared content type and file signature, enforces a 10 MB limit, stores the file on local disk, creates a `doc_`-prefixed UUID, and schedules text extraction in a background task. A successful response uses HTTP `202` and has this shape:

```json
{"document_id": "doc_<uuid>", "status": "processing"}
```

Files are stored in `data/documents` by default; `DOCUMENT_STORAGE_DIR` can override the directory. `tools/extract_text.py` extracts embedded PDF text with `pypdf`, falls back to Tesseract OCR for scanned PDF pages, and uses Tesseract OCR for JPG/PNG uploads. `agent/pipeline.py` orchestrates text extraction, LLM extraction, validation, and summary generation. Final results are persisted to `data/results/<document_id>.json` by default; `DOCUMENT_RESULTS_DIR` can override the results directory. Poll `GET /documents/{document_id}` for the active processing step and final output. Tesseract must be installed as a system executable, and LLM calls require `OPENAI_API_KEY`.

The intended pipeline remains staged so each part can be tested and improved independently:

1. **Text extraction:** implemented with PDF text parsing and Tesseract OCR fallback.
2. **Structured extraction:** implemented with an OpenAI structured-output response and a Pydantic `InvoiceData` schema.
3. **Validation:** `tools/validate_invoice.py` checks missing fields, currency format, date format, and line-item totals before summary generation.
4. **Summary:** generated from validated invoice fields by a separate LLM call.
5. **Progress and result retrieval:** `GET /documents/{document_id}` returns the active step or final output.

Keep model- or provider-specific code behind small interfaces so those dependencies can be changed without rewriting the workflow.

## Prompt Design

The extraction prompt asks the model to use only document-supported information and return null for absent or unreadable values. Structured output is constrained by `InvoiceData`, then validated in application code before the summary call. The summary prompt receives validated fields and validation findings; it is instructed not to invent missing values.

Keep extraction and summarization separate. Extraction should be faithful to the source; summarization should use validated fields and avoid introducing facts. Include relevant page or text evidence with extracted values when available, and represent uncertainty explicitly. Version prompts and evaluate changes against a small set of representative invoices and receipts.

## Limitations

- The upload and agent pipeline are implemented, but processing status is held in memory and is lost on API restart.
- LLM calls require an OpenAI API key and internet access; provider errors or invalid output fail the document task.
- The current invoice schema and validation rules are intentionally small and are not a complete accounting or tax validation system.
- Tesseract OCR requires a separately installed system executable; OCR accuracy and language configuration are not yet evaluated.
- Processing uses FastAPI in-process background tasks, which are not durable across process restarts and are not suitable for reliable long-running production jobs.
- Uploaded files are stored on local disk with no persistence metadata, retention policy, or cleanup mechanism.
- Validation checks the upload content type and file signature; it does not deeply inspect or scan files.
- There is no automated test suite yet, so behavior beyond the manually checked upload flow is unverified.
- OCR and vision quality can vary with image resolution, rotation, handwriting, layout, and scan quality.
- Financial documents differ by vendor, locale, currency, and tax conventions; ambiguous values may need review.
- The API does not yet define authentication, authorization, privacy controls, or service-provider dependencies.
- Model output may omit fields, misread values, or be malformed. Schema validation can reduce, but not eliminate, these errors.

## Production Improvements

Before production, prioritize:

1. Replace or complement in-process background tasks with a durable job queue; persist processing status and provide a way to retrieve results.
2. Use managed object storage for documents and define retention, deletion, and backup policies.
3. Add authentication, authorization, encryption, upload quotas, malware scanning, and redacted logs for sensitive financial data.
4. Define versioned schemas and enforce them at every model and API boundary; preserve evidence and uncertainty for extracted fields.
5. Build a representative evaluation set; measure field-level accuracy and document-level success, and add regression tests for upload, processing, and prompt/model changes.
6. Add human review for low-confidence, missing, or contradictory financial fields.
7. Add timeouts, safe retries, rate limits, observability, and clear error responses. Test malformed files, multi-page documents, locale variations, and degraded OCR.
