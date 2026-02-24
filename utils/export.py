"""
Export utilities — converts approved polls to CSV or JSON for download/API push.
"""
import json
import csv
import io
from typing import List, Dict


def export_polls_to_json(polls: List[Dict]) -> str:
    """Export polls as a formatted JSON string."""
    export_data = []
    for poll in polls:
        export_data.append({
            "id": poll.get("id"),
            "question": poll.get("question"),
            "category": poll.get("category"),
            "resolution": poll.get("resolution"),
            "deadline": poll.get("deadline"),
            "token_pool": poll.get("token_pool"),
            "controversy_score": poll.get("controversy_score"),
            "tags": poll.get("tags", []),
            "yes_argument": poll.get("yes_argument"),
            "no_argument": poll.get("no_argument"),
            "source": poll.get("source"),
            "approved_at": poll.get("approved_at"),
        })
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def export_polls_to_csv(polls: List[Dict]) -> str:
    """Export polls as a CSV string."""
    output = io.StringIO()
    fieldnames = [
        "id", "question", "category", "resolution", "deadline",
        "token_pool", "controversy_score", "tags", "source", "approved_at"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for poll in polls:
        row = dict(poll)
        row["tags"] = ", ".join(poll.get("tags", []))
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return output.getvalue()
