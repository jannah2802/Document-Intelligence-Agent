import re
from datetime import date
from typing import TypedDict

from agent.schemas import InvoiceData


class InvoiceValidation(TypedDict):
    structured_data: dict[str, object]
    is_valid: bool
    missing_fields: list[str]
    warnings: list[str]


def validate_invoice(data: InvoiceData | dict[str, object]) -> InvoiceValidation:
    """Validate invoice fields and flag missing values or inconsistent totals."""
    invoice = InvoiceData.model_validate(data)
    normalized = invoice.model_dump(mode="json")
    currency = normalized["currency"]
    if isinstance(currency, str):
        normalized["currency"] = currency.strip().upper()

    required_fields = ("vendor", "invoice_number", "invoice_date", "currency", "total_amount")
    missing_fields = [
        field
        for field in required_fields
        if normalized[field] is None
        or (isinstance(normalized[field], str) and not normalized[field].strip())
    ]
    warnings: list[str] = []

    normalized_currency = normalized["currency"]
    if normalized_currency is not None and not re.fullmatch(r"[A-Z]{3}", normalized_currency):
        warnings.append("currency should be a three-letter ISO code")

    for field in ("invoice_date", "due_date"):
        value = normalized[field]
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                warnings.append(f"{field} should use YYYY-MM-DD format")

    line_items = normalized["line_items"]
    total_amount = normalized["total_amount"]
    if line_items and total_amount is not None and all(
        item["amount"] is not None for item in line_items
    ):
        items_total = sum(item["amount"] for item in line_items)
        tolerance = max(0.02, abs(total_amount) * 0.01)
        if abs(items_total - total_amount) > tolerance:
            warnings.append(
                "line-item amounts differ from invoice total; taxes or fees may explain the difference"
            )

    return {
        "structured_data": normalized,
        "is_valid": not missing_fields and not warnings,
        "missing_fields": missing_fields,
        "warnings": warnings,
    }