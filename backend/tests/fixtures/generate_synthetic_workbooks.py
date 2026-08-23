"""
Generates synthetic .xlsx workbooks for the POC demo and tests.

Run with:  python tests/fixtures/generate_synthetic_workbooks.py
Produces files in tests/fixtures/:
  clean_urban.xlsx        - all Urban Street, all valid -> all GREEN
  clean_rural_road.xlsx   - all Rural Road, all valid -> all GREEN
  mixed_batch.xlsx        - one row per combination, mixed outcomes
"""

import os

import pandas as pd

FIXTURES_DIR = os.path.dirname(__file__)


def _row(**kwargs) -> dict:
    base = {
        "batchId": None,
        "rowId": None,
        "objectId": 1000,
        "servicePointKey": "SPK-0001",
        "distributionSiteId": "DSID-0001",
        "addressType": "Civic",
        "addressCombination": "UrbanStreet",
        "unitDesignator": None,
        "unitNumber": None,
        "houseNumber": None,
        "streetPreDirection": None,
        "streetName": None,
        "streetTypeCode": None,
        "streetDirection": None,
        "cityQuadrant": None,
        "cityTownName": None,
        "province": "AB",
        "lsd": None,
        "lsdQuadrant": None,
        "quarterSectionCode": None,
        "section": None,
        "township": None,
        "range": None,
        "meridian": None,
        "ruralHouseNumber": None,
        "legalLot": None,
        "lotRangeId": None,
        "block": None,
        "governmentPlanId": None,
        "addressPreRoadNumber": None,
        "addressRoadType": None,
        "addressPostRoadNumber": None,
        "areaName": None,
        "postalCode": None,
        "changedBy": "poc.demo@atco.com",
    }
    base.update(kwargs)
    return base


def clean_urban_rows() -> list[dict]:
    rows = []
    for i in range(1, 6):
        rows.append(
            _row(
                objectId=1000 + i,
                servicePointKey=f"SPK-{1000 + i}",
                distributionSiteId=f"DSID-{1000 + i}",
                addressType="Civic",
                addressCombination="UrbanStreet",
                houseNumber=str(100 + i),
                streetName=f"Maple Street {i}",
                streetTypeCode="ST",
                cityTownName="Calgary",
                postalCode="T2P1J9",
            )
        )
    return rows


def clean_rural_road_rows() -> list[dict]:
    rows = []
    for i in range(1, 6):
        rows.append(
            _row(
                objectId=2000 + i,
                servicePointKey=f"SPK-{2000 + i}",
                distributionSiteId=f"DSID-{2000 + i}",
                addressType="Rural",
                addressCombination="RuralRoad",
                addressPreRoadNumber=str(10 + i),
                addressRoadType="RR",
                addressPostRoadNumber=str(220 + i),
                province="AB",
            )
        )
    return rows


def mixed_batch_rows() -> list[dict]:
    return [
        # 1. Urban Street - clean -> GREEN
        _row(
            objectId=3001,
            servicePointKey="SPK-3001",
            distributionSiteId="DSID-3001",
            addressType="Civic",
            addressCombination="UrbanStreet",
            houseNumber="482",
            streetName="Willow Avenue",
            streetTypeCode="AVE",
            cityTownName="Edmonton",
            postalCode="T5J0N3",
        ),
        # 2. Urban Street - missing required streetName -> RED (rule)
        _row(
            objectId=3002,
            servicePointKey="SPK-3002",
            distributionSiteId="DSID-3002",
            addressType="Civic",
            addressCombination="UrbanStreet",
            houseNumber="17",
            cityTownName="Edmonton",
        ),
        # 3. LLD/ATS Quarter - clean -> GREEN
        _row(
            objectId=3003,
            servicePointKey="SPK-3003",
            distributionSiteId="DSID-3003",
            addressType="Legal",
            addressCombination="LLD_ATS_Quarter",
            quarterSectionCode="NE",
            section="12",
            township="45",
            range="10",
            meridian="W4",
        ),
        # 4. LLD/ATS LSD - not-allowed field populated (cityTownName) -> RED (rule)
        _row(
            objectId=3004,
            servicePointKey="SPK-3004",
            distributionSiteId="DSID-3004",
            addressType="Legal",
            addressCombination="LLD_ATS_LSD",
            lsd="04",
            section="12",
            township="45",
            range="10",
            meridian="W4",
            cityTownName="Should Not Be Here",
        ),
        # 5. Lot Block Plan - clean -> GREEN
        _row(
            objectId=3005,
            servicePointKey="SPK-3005",
            distributionSiteId="DSID-3005",
            addressType="Legal",
            addressCombination="LotBlockPlan",
            legalLot="7",
            block="3",
            governmentPlanId="8021144",
            cityTownName="Red Deer",
        ),
        # 6. Rural Road - clean but with geocoder ALT token -> AMBER
        _row(
            objectId=3006,
            servicePointKey="SPK-3006",
            distributionSiteId="DSID-3006",
            addressType="Rural",
            addressCombination="RuralRoad",
            addressPreRoadNumber="RR ALT 220",
            addressRoadType="RR",
            addressPostRoadNumber="30",
        ),
        # 7. Rural Street - clean but with DRIFT token -> AMBER
        _row(
            objectId=3007,
            servicePointKey="SPK-3007",
            distributionSiteId="DSID-3007",
            addressType="Rural",
            addressCombination="RuralStreet",
            streetPreDirection="N",
            streetName="DRIFT Range Road 55",
            streetTypeCode="RD",
            quarterSectionCode="SW",
            section="8",
            township="20",
            range="5",
            meridian="W5",
        ),
        # 8. Urban Street - NOMATCH geocoding token -> RED (geocode)
        _row(
            objectId=3008,
            servicePointKey="SPK-3008",
            distributionSiteId="DSID-3008",
            addressType="Civic",
            addressCombination="UrbanStreet",
            houseNumber="9",
            streetName="NOMATCH Nowhere Lane",
            streetTypeCode="LN",
            cityTownName="Lethbridge",
        ),
        # 9. Urban Street - missing Maximo linking field (distributionSiteId) -> RED (pre-dispatch)
        _row(
            objectId=3009,
            servicePointKey="SPK-3009",
            distributionSiteId=None,
            addressType="Civic",
            addressCombination="UrbanStreet",
            houseNumber="55",
            streetName="Birch Boulevard",
            streetTypeCode="BLVD",
            cityTownName="Calgary",
        ),
        # 10. Rural Road - Maximo schema conflict token -> RED (pre-dispatch)
        _row(
            objectId=3010,
            servicePointKey="SPK-MAXCONFLICT-3010",
            distributionSiteId="DSID-3010",
            addressType="Rural",
            addressCombination="RuralRoad",
            addressPreRoadNumber="12",
            addressRoadType="RR",
            addressPostRoadNumber="221",
        ),
    ]


def write_workbook(rows: list[dict], filename: str) -> None:
    for i, row in enumerate(rows, start=1):
        row["rowId"] = i
    df = pd.DataFrame(rows)
    path = os.path.join(FIXTURES_DIR, filename)
    df.to_excel(path, index=False)
    print(f"wrote {path} ({len(rows)} rows)")


if __name__ == "__main__":
    write_workbook(clean_urban_rows(), "clean_urban.xlsx")
    write_workbook(clean_rural_road_rows(), "clean_rural_road.xlsx")
    write_workbook(mixed_batch_rows(), "mixed_batch.xlsx")
