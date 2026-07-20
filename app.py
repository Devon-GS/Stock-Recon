from __future__ import annotations

import csv
import io
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, Response, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("INVENTORY_DB_PATH", str(BASE_DIR / "inventory.db")))

DATASET_DEFINITIONS = {
    "opening": {"label": "Opening Stock", "quantity_column": 7},
    "purchases": {"label": "Purchases", "quantity_column": 6},
    "sales": {"label": "Sales", "quantity_column": 5},
    "closing": {"label": "Closing Stock", "quantity_column": 7},
}


@dataclass
class ParsedRow:
    dataset_type: str
    description: str
    stock_code: str
    quantity: Decimal
    source_filename: str
    source_row: int


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "inventory-usage-secret-key"

    init_db()

    @app.get("/")
    def index() -> str:
        items, summary = build_comparison()
        return render_template("index.html", items=items, summary=summary)

    @app.post("/upload")
    def upload() -> str:
        try:
            parsed_rows = parse_uploaded_files(request.files)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

        save_rows(parsed_rows)
        flash("CSV files imported successfully.", "success")
        return redirect(url_for("index"))

    @app.get("/export")
    def export_results() -> Response:
        items, summary = build_comparison()
        return build_export_response(items, summary, "inventory_comparison")

    @app.get("/export-mismatches")
    def export_mismatches() -> Response:
        items, summary = build_comparison()
        mismatch_items = [item for item in items if not item["match"]]
        mismatch_summary = {
            "item_count": len(mismatch_items),
            "discrepancy_count": len(mismatch_items),
        }
        return build_export_response(mismatch_items, mismatch_summary, "inventory_mismatches")

    return app


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_type TEXT NOT NULL,
                description TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                quantity TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                source_row INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_uploaded_files(files) -> list[ParsedRow]:
    required_fields = list(DATASET_DEFINITIONS.keys())
    parsed_rows: list[ParsedRow] = []

    for dataset_type in required_fields:
        uploaded = files.get(dataset_type)
        if uploaded is None or uploaded.filename == "":
            raise ValueError(f"Please upload a CSV file for {DATASET_DEFINITIONS[dataset_type]['label']}.")

        source_filename = secure_filename(uploaded.filename) or f"{dataset_type}.csv"
        content = uploaded.read()
        if not content:
            raise ValueError(f"{source_filename} is empty.")

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("cp1252")

        parsed_rows.extend(parse_csv_rows(text, dataset_type, source_filename))

    return parsed_rows


def parse_csv_rows(text: str, dataset_type: str, source_filename: str) -> list[ParsedRow]:
    dataset_definition = DATASET_DEFINITIONS[dataset_type]
    quantity_column = dataset_definition["quantity_column"]
    output: list[ParsedRow] = []

    reader = csv.reader(io.StringIO(text))
    for row_number, row in enumerate(reader, start=1):
        if not row or all(not cell.strip() for cell in row):
            continue

        description = row[0].strip() if len(row) > 0 else ""
        stock_code = row[1].strip() if len(row) > 1 else ""
        quantity_raw = row[quantity_column].strip() if len(row) > quantity_column else ""

        if is_header_row(description, stock_code, dataset_type, quantity_raw):
            continue

        if not description and not stock_code:
            continue

        if len(row) <= quantity_column or len(row) < 2:
            raise ValueError(
                f"{source_filename} row {row_number} does not have enough columns for {dataset_definition['label']}."
            )

        if not description:
            raise ValueError(f"{source_filename} row {row_number} is missing a description.")
        if not stock_code:
            raise ValueError(f"{source_filename} row {row_number} is missing a stock code.")

        quantity = parse_decimal(quantity_raw, source_filename, row_number)
        output.append(
            ParsedRow(
                dataset_type=dataset_type,
                description=description,
                stock_code=stock_code,
                quantity=quantity,
                source_filename=source_filename,
                source_row=row_number,
            )
        )

    if not output:
        raise ValueError(f"{source_filename} did not contain any usable rows.")

    return output


def is_header_row(description: str, stock_code: str, dataset_type: str, quantity_raw: str = "") -> bool:
    description_lower = description.strip().lower()
    stock_code_lower = stock_code.strip().lower()
    quantity_lower = quantity_raw.strip().lower()

    if description_lower in {"description", "stock description"} and stock_code_lower in {"stock code", "stockcode"}:
        return True

    if stock_code_lower == "stock code":
        return True

    if description_lower in {"stock description", "description"}:
        return True

    expected_keyword = {
        "opening": "stock on hand",
        "closing": "stock on hand",
        "purchases": "quantity purchased",
        "sales": "quantity sold",
    }[dataset_type]

    return expected_keyword in quantity_lower or expected_keyword.replace(" ", "") in quantity_lower


def parse_decimal(value: str, source_filename: str, row_number: int) -> Decimal:
    cleaned = value.replace(",", "").replace(" ", "")
    if cleaned == "":
        raise ValueError(f"{source_filename} row {row_number} is missing a quantity value.")

    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"{source_filename} row {row_number} has an invalid numeric value: {value!r}.") from exc


def save_rows(rows: list[ParsedRow]) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM imports")
        conn.executemany(
            """
            INSERT INTO imports (
                dataset_type,
                description,
                stock_code,
                quantity,
                source_filename,
                source_row,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.dataset_type,
                    row.description,
                    row.stock_code,
                    str(row.quantity),
                    row.source_filename,
                    row.source_row,
                    datetime.utcnow().isoformat(timespec="seconds"),
                )
                for row in rows
            ],
        )


def build_comparison() -> tuple[list[dict], dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT dataset_type, description, stock_code, quantity
            FROM imports
            ORDER BY stock_code, id
            """
        ).fetchall()

    grouped: dict[str, dict] = defaultdict(
        lambda: {
            "description": "",
            "opening": Decimal("0"),
            "purchases": Decimal("0"),
            "sales": Decimal("0"),
            "closing": Decimal("0"),
        }
    )

    for row in rows:
        stock_code = row["stock_code"]
        item = grouped[stock_code]
        if not item["description"] and row["description"]:
            item["description"] = row["description"]
        item[row["dataset_type"]] += Decimal(row["quantity"])

    items: list[dict] = []
    discrepancy_count = 0

    for stock_code, item in sorted(grouped.items(), key=lambda entry: entry[0]):
        expected_closing = item["opening"] + item["purchases"] - item["sales"]
        variance = expected_closing - item["closing"]
        is_match = variance == 0
        if not is_match:
            discrepancy_count += 1

        items.append(
            {
                "description": item["description"],
                "stock_code": stock_code,
                "opening": item["opening"],
                "purchases": item["purchases"],
                "sales": item["sales"],
                "expected_closing": expected_closing,
                "closing": item["closing"],
                "variance": variance,
                "match": is_match,
            }
        )

    summary = {
        "item_count": len(items),
        "discrepancy_count": discrepancy_count,
    }
    return items, summary


def build_export_response(items: list[dict], summary: dict, filename_prefix: str) -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Description",
            "Stock Code",
            "Opening",
            "Purchases",
            "Sales",
            "Expected Closing",
            "Actual Closing",
            "Variance",
            "Status",
        ]
    )

    for item in items:
        writer.writerow(
            [
                item["description"],
                item["stock_code"],
                item["opening"],
                item["purchases"],
                item["sales"],
                item["expected_closing"],
                item["closing"],
                item["variance"],
                "Match" if item["match"] else "Check",
            ]
        )

    writer.writerow([])
    writer.writerow(["Summary", "Item Count", summary["item_count"], "Mismatch Count", summary["discrepancy_count"]])

    csv_data = output.getvalue()
    filename = f"{filename_prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
