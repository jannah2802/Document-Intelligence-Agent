import json
import os

from openai import OpenAI

from agent.schemas import InvoiceData


def _client() -> OpenAI:
    return OpenAI()


def extract_invoice_data(raw_text: str) -> InvoiceData:
    if not raw_text.strip():
        raise ValueError("Cannot extract invoice fields from empty document text")

    response = _client().chat.completions.parse(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract invoice data from the supplied document text. "
                    "Do not infer missing values; use null when a value is absent or unreadable. "
                    "Return dates as YYYY-MM-DD when unambiguous. Include line items only "
                    "when supported by the text."
                ),
            },
            {"role": "user", "content": raw_text},
        ],
        response_format=InvoiceData,
    )
    message = response.choices[0].message
    if message.refusal:
        raise RuntimeError("The model refused to extract this document")
    if message.parsed is None:
        raise RuntimeError("The model returned no structured invoice data")
    return message.parsed


def generate_summary(invoice: InvoiceData, validation: dict[str, object]) -> str:
    response = _client().chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a concise one-sentence invoice summary using only the supplied "
                    "validated fields. Do not invent missing information. If important fields "
                    "are absent, state that they were not identified."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "invoice": invoice.model_dump(mode="json"),
                        "validation": validation,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.2,
    )
    summary = response.choices[0].message.content
    if not summary or not summary.strip():
        raise RuntimeError("The model returned an empty invoice summary")
    return summary.strip()