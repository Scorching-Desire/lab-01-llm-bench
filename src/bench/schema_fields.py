"""Typed extraction contract for synthetic makerspace service receipts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocFields(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    doc_no: str = Field(pattern=r"^MS-\d{4}$")
    total: float
    issued_on: date
    items: list[str] = Field(min_length=1)
    note: str | None
    label: Literal["ремонт", "доступ", "оплата", "інше"]
