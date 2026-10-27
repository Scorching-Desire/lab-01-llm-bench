"""Strict output schema; the label is the task's only required field."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TicketLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Literal["ремонт", "доступ", "оплата", "інше"]
