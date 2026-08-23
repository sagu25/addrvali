"""
Capability 2: Geocoding Analyzer - MOCKED for the POC.

In production this wraps ATCO's existing (reconfigured) geocoder REST
service. For the synthetic-data POC there is no real geocoder to call, so
this module simulates one deterministically: given the same address text
it always returns the same confidence/candidates/drift, so demos are
repeatable instead of randomly flaky.

Synthetic test data can force a specific outcome by including one of the
magic tokens below anywhere in the address text (case-insensitive):
  NOMATCH   -> no candidate found (RED)
  LOWCONF   -> low confidence single match (RED)
  ALT       -> moderate confidence with alternate candidates (AMBER)
  DRIFT     -> match found but far from the expected Service Point location (AMBER)
Any address without a magic token gets a stable hash-derived high-confidence
match (GREEN).

Swap this module out for a real HTTP client against ATCO's geocoder when
that dependency is confirmed - the ValidationComponentResult contract
(errors/warnings/metadata) stays the same either way.
"""

import hashlib

from app.models.address_models import (
    BulkAddressCsvRow,
    ValidationComponentResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationStatus,
)

COMPONENT_NAME = "GeocodingAnalyzer"

HIGH_CONFIDENCE = 0.95
MODERATE_CONFIDENCE = 0.70
LOW_CONFIDENCE = 0.40


def _address_text(row: BulkAddressCsvRow) -> str:
    parts = [
        row.houseNumber,
        row.streetPreDirection,
        row.streetName,
        row.streetTypeCode,
        row.streetDirection,
        row.ruralHouseNumber,
        row.addressPreRoadNumber,
        row.addressRoadType,
        row.addressPostRoadNumber,
        row.cityTownName,
        row.province,
        row.postalCode,
        row.areaName,
    ]
    return " ".join(str(p) for p in parts if p)


def _stable_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _fake_coordinates(text: str) -> tuple[float, float]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    lat = 49.0 + (int(digest[8:16], 16) / 0xFFFFFFFF) * 10.0  # roughly Alberta
    lon = -120.0 - (int(digest[16:24], 16) / 0xFFFFFFFF) * 10.0
    return round(lat, 6), round(lon, 6)


def analyze(row: BulkAddressCsvRow) -> ValidationComponentResult:
    text = _address_text(row)
    text_upper = text.upper()

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    lat, lon = _fake_coordinates(text)
    metadata = {"queriedAddress": text}

    if not text.strip():
        errors.append(
            ValidationIssue(
                message="No address text was available to geocode.",
                severity=ValidationSeverity.ERROR,
            )
        )
        return ValidationComponentResult(
            componentName=COMPONENT_NAME,
            status=ValidationStatus.RED,
            errors=errors,
            metadata=metadata,
        )

    if "NOMATCH" in text_upper:
        errors.append(
            ValidationIssue(
                message="Geocoder returned no candidate match for this address.",
                severity=ValidationSeverity.ERROR,
            )
        )
        metadata["confidence"] = 0.0
        metadata["candidates"] = []
        status = ValidationStatus.RED

    elif "LOWCONF" in text_upper:
        confidence = LOW_CONFIDENCE
        errors.append(
            ValidationIssue(
                message=f"Geocoder match confidence ({confidence:.2f}) is below the acceptable threshold.",
                severity=ValidationSeverity.ERROR,
            )
        )
        metadata["confidence"] = confidence
        metadata["candidates"] = [{"lat": lat, "lon": lon, "score": confidence}]
        status = ValidationStatus.RED

    elif "ALT" in text_upper:
        confidence = MODERATE_CONFIDENCE
        warnings.append(
            ValidationIssue(
                message=(
                    f"Geocoder match confidence ({confidence:.2f}) is moderate and "
                    "alternate candidates exist - review before dispatch."
                ),
                severity=ValidationSeverity.WARNING,
            )
        )
        alt_lat, alt_lon = _fake_coordinates(text + "|alt")
        metadata["confidence"] = confidence
        metadata["candidates"] = [
            {"lat": lat, "lon": lon, "score": confidence},
            {"lat": alt_lat, "lon": alt_lon, "score": confidence - 0.05},
        ]
        status = ValidationStatus.AMBER

    elif "DRIFT" in text_upper:
        warnings.append(
            ValidationIssue(
                message="Geocoded location is a significant distance from the expected Service Point location.",
                severity=ValidationSeverity.WARNING,
            )
        )
        metadata["confidence"] = HIGH_CONFIDENCE
        metadata["candidates"] = [{"lat": lat, "lon": lon, "score": HIGH_CONFIDENCE}]
        metadata["driftDetected"] = True
        metadata["driftMeters"] = 1500 + int(_stable_unit_interval(text) * 3000)
        status = ValidationStatus.AMBER

    else:
        metadata["confidence"] = HIGH_CONFIDENCE
        metadata["candidates"] = [{"lat": lat, "lon": lon, "score": HIGH_CONFIDENCE}]
        metadata["driftDetected"] = False
        status = ValidationStatus.GREEN

    metadata["coordinates"] = {"lat": lat, "lon": lon}

    return ValidationComponentResult(
        componentName=COMPONENT_NAME,
        status=status,
        errors=errors,
        warnings=warnings,
        metadata=metadata,
    )
