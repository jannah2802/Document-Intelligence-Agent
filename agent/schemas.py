from pydantic import BaseModel, ConfigDict


class InvoiceLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    description: str | None
    quantity: float | None
    unit_price: float | None
    amount: float | None


class InvoiceData(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    vendor: str | None
    invoice_number: str | None
    invoice_date: str | None
    due_date: str | None
    currency: str | None
    total_amount: float | None
    line_items: list[InvoiceLineItem] | None