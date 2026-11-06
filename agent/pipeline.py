from pathlib import Path
from typing import Callable

from agent.llm import extract_invoice_data, generate_summary
from agent.schemas import InvoiceData
from tools.extract_text import extract_text
from tools.validate_invoice import validate_invoice


def run_document_agent(
    document_id: str,
    document_path: Path,
    update_step: Callable[[str], None],
) -> dict[str, object]:
    """Run text extraction, structured extraction, validation, and summarization."""
    update_step("extracting_text")
    text_result = extract_text(document_id, document_path)
    if not text_result["raw_text"].strip():
        raise ValueError("No text could be extracted from this document")

    update_step("extracting_fields")
    invoice = extract_invoice_data(text_result["raw_text"])

    update_step("validating")
    validation = validate_invoice(invoice)
    validated_invoice = InvoiceData.model_validate(validation["structured_data"])

    update_step("generating_summary")
    summary = generate_summary(validated_invoice, validation)

    return {
        "document_id": document_id,
        "structured_data": validation["structured_data"],
        "validation": {
            "is_valid": validation["is_valid"],
            "missing_fields": validation["missing_fields"],
            "warnings": validation["warnings"],
        },
        "summary": summary,
    }