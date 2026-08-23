"""
Reads an uploaded .xlsx workbook into a list of BulkAddressCsvRow.

Accepts either the model's own field names as headers (batchId,
houseNumber, streetName, ...) or the more business-friendly "Site Catalog
Name" headers from the ESRI table (House Number, Street Name, City/Town
Name, ...) - both are mapped to the same Pydantic fields so a workbook
built directly from the source table still parses.
"""

import io
from dataclasses import dataclass, field

import pandas as pd
from pydantic import ValidationError

from app.models.address_models import BulkAddressCsvRow

# Site Catalog Name (and a few common variants) -> model field name.
HEADER_ALIASES: dict[str, str] = {
    "batchid": "batchId",
    "rowid": "rowId",
    "objectid": "objectId",
    "object id": "objectId",
    "servicepointkey": "servicePointKey",
    "service point key": "servicePointKey",
    "distributionsiteid": "distributionSiteId",
    "distribution site id": "distributionSiteId",
    "addresstype": "addressType",
    "address type": "addressType",
    "addresscombination": "addressCombination",
    "address combination": "addressCombination",
    "unit designator": "unitDesignator",
    "unit number": "unitNumber",
    "house number": "houseNumber",
    "street predirection": "streetPreDirection",
    "street pre direction": "streetPreDirection",
    "street name": "streetName",
    "street type code": "streetTypeCode",
    "street type": "streetTypeCode",
    "street direction": "streetDirection",
    "street post direction": "streetDirection",
    "city quadrant": "cityQuadrant",
    "city/town name": "cityTownName",
    "city / town / municipality": "cityTownName",
    "city town name": "cityTownName",
    "province": "province",
    "state / province": "province",
    "legal subdivision code (lsd)": "lsd",
    "legal subdivision": "lsd",
    "lsd": "lsd",
    "lsd quadrant": "lsdQuadrant",
    "legal subdivision quadrant": "lsdQuadrant",
    "quarter section code": "quarterSectionCode",
    "quarter": "quarterSectionCode",
    "section": "section",
    "township": "township",
    "range": "range",
    "meridian": "meridian",
    "rural house number": "ruralHouseNumber",
    "legal lot": "legalLot",
    "lot": "legalLot",
    "lot range id": "lotRangeId",
    "block": "block",
    "government plan id": "governmentPlanId",
    "plan": "governmentPlanId",
    "address pre-road number": "addressPreRoadNumber",
    "address pre road number": "addressPreRoadNumber",
    "address road type": "addressRoadType",
    "address post-road number": "addressPostRoadNumber",
    "address post road number": "addressPostRoadNumber",
    "area name": "areaName",
    "postal code": "postalCode",
    "changed by": "changedBy",
    "changedby": "changedBy",
}


def _normalise_header(header: str) -> str:
    key = str(header).strip().lower()
    if key in HEADER_ALIASES:
        return HEADER_ALIASES[key]
    # If it's already a valid model field name (any case), keep it as-is.
    return header


@dataclass
class ParsedWorkbook:
    rows: list[BulkAddressCsvRow] = field(default_factory=list)
    row_errors: list[dict] = field(default_factory=list)  # {"rowId": int, "error": str}


def parse_workbook(file_bytes: bytes, batch_id: str | None = None) -> ParsedWorkbook:
    df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    df = df.rename(columns={col: _normalise_header(col) for col in df.columns})
    df = df.where(pd.notnull(df), None)

    parsed = ParsedWorkbook()
    for excel_row_index, record in enumerate(df.to_dict(orient="records")):
        row_id = excel_row_index + 1
        record = {k: v for k, v in record.items() if k in BulkAddressCsvRow.model_fields}
        record.setdefault("rowId", row_id)
        if batch_id:
            record["batchId"] = batch_id

        try:
            parsed.rows.append(BulkAddressCsvRow(**record))
        except ValidationError as exc:
            parsed.row_errors.append(
                {"rowId": row_id, "error": exc.errors()[0]["msg"] if exc.errors() else str(exc)}
            )

    return parsed
