"""Synthetic makerspace inventory and bookings; no personal or employer data."""
import json
import re
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ConfigDict, ValidationError

from bench.clients import to_strict_schema

STATIONS = {"M-101": "несправна", "M-102": "справна", "M-103": "несправна", "M-104": "справна"}
BOOKINGS = {"B-201": "не оплачено", "B-202": "оплачено", "B-203": "не оплачено", "B-204": "оплачено"}


class StationArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    station_id: str


class BookingArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    booking_id: str


def station_status(args: StationArgs) -> str:
    if not re.fullmatch(r"M-\d{3}", args.station_id):
        raise ValueError("station_id must match M-123")
    return json.dumps({"station_id": args.station_id, "status": STATIONS.get(args.station_id, "не знайдено")},
                      ensure_ascii=False)


def booking_status(args: BookingArgs) -> str:
    if not re.fullmatch(r"B-\d{3}", args.booking_id):
        raise ValueError("booking_id must match B-123")
    return json.dumps({"booking_id": args.booking_id, "status": BOOKINGS.get(args.booking_id, "не знайдено")},
                      ensure_ascii=False)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[[BaseModel], str]


TOOLS = {t.name: t for t in (
    Tool("station_status", "Стан навчальної станції за station_id формату M-123.", StationArgs, station_status),
    Tool("booking_status", "Стан оплати бронювання за booking_id формату B-123.", BookingArgs, booking_status),
)}


def tool_specs(names: list[str]) -> list[dict]:
    return [{"type": "function", "function": {"name": n, "description": TOOLS[n].description,
             "parameters": to_strict_schema(TOOLS[n].args_model), "strict": True}} for n in names]


def execute(name: str, arguments_raw: str) -> tuple[str, str | None]:
    tool = TOOLS.get(name)
    if tool is None:
        return f"unknown tool: {name}", "unknown_tool"
    try:
        args = tool.args_model.model_validate_json(arguments_raw or "{}")
    except ValidationError as e:
        return f"bad arguments: {e.errors(include_url=False)}", "bad_args"
    try:
        return tool.fn(args), None
    except Exception as e:
        return f"tool error: {e}", "tool_error"
