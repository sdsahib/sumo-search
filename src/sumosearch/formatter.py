from __future__ import annotations

import csv
import io
import json

from sumosearch.exceptions import ValidationError
from sumosearch.models import LogMessage

VALID_FORMATS = ("text", "json", "csv")


def format_messages(messages: list[LogMessage], fmt: str) -> str:
    if fmt not in VALID_FORMATS:
        raise ValidationError(
            f"unknown format '{fmt}'; must be one of: {', '.join(VALID_FORMATS)}"
        )

    if fmt == "text":
        if not messages:
            return "No results found."
        lines = []
        for msg in messages:
            if "_raw" in msg.fields:
                lines.append(msg.fields["_raw"])
            else:
                lines.append(
                    "\t".join(f"{k}={v}" for k, v in msg.fields.items())
                )
        return "\n".join(lines)

    if fmt == "json":
        return json.dumps([m.fields for m in messages], indent=2)

    # csv
    if not messages:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["_raw"])
        return buf.getvalue()

    all_keys: set[str] = set()
    for msg in messages:
        all_keys.update(msg.fields.keys())
    header = sorted(all_keys)

    buf = io.StringIO()
    dict_writer: csv.DictWriter[str] = csv.DictWriter(
        buf, fieldnames=header, extrasaction="ignore"
    )
    dict_writer.writeheader()
    for msg in messages:
        row = {k: msg.fields.get(k, "") for k in header}
        dict_writer.writerow(row)
    return buf.getvalue()
