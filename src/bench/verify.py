"""Rules for makerspace receipts, independent of benchmark expectations."""

from bench.score import norm_date, norm_number


def check(fields):
    if fields is None:
        return [dict(code="schema", message="Потрібен JSON за схемою документа.", fields=[])]
    flags = []
    raw_date = fields.get("issued_on")
    if not isinstance(raw_date, str) or norm_date(raw_date) is None:
        flags.append(dict(code="format.issued_on", message="Подайте дату документа у форматі YYYY-MM-DD.",
                          fields=["issued_on"]))
    total = norm_number(fields.get("total"))
    if total is None or not 0 < total <= 100000:
        flags.append(dict(code="range.total", message="Підсумок у гривнях має бути понад 0 і до 100000 включно.",
                          fields=["total"]))
    if fields.get("label") == "інше" and not (fields.get("note") or "").strip():
        flags.append(dict(code="cross.note_required", message="Для маршруту «інше» перенесіть примітку документа.",
                          fields=["label", "note"]))
    return flags
