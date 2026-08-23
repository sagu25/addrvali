"""
ESRI Address Validation rule matrix, transcribed from the ATCO-approved
combinations table (sequences 8-36).

Six address combinations (columns in the source table):
  1. URBAN_STREET      - Urban (Street Format Address)
  2. LLD_ATS_QUARTER    - LLD / ATS - Quarter
  3. LLD_ATS_LSD         - LLD / ATS - LSD
  4. LOT_BLOCK_PLAN      - Lot Block Plan
  5. RURAL_ROAD          - Rural (Road Format Address)
  6. RURAL_STREET        - Rural (Street Format Address)

NOTE: rows for sequence #30-31 were not captured in the source screenshot
(the table jumps from Government Plan ID [29] to Address Lot ID [32]).
Confirm those two fields with the signed-off matrix before treating this
config as final - see README "Known gaps".

The source table also carries a footnote on combination 6 (Rural Street):
"if one of the Optional fields are populated for sequence #'s 8 through
[LSD?], then all required fields as shown in this combination are
populated." That is a conditional rule layered on top of the base
Required/Optional/Not Allowed/N-A grid below, not yet encoded here -
flagged in rules/validator.py as a TODO rather than guessed at.
"""

from enum import Enum


class FieldRule(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    NOT_ALLOWED = "NOT_ALLOWED"
    NA = "N/A"


# Canonical field names -> attribute names on BulkAddressCsvRow.
# (Site Catalog Name from the source table, mapped to the model's field names.)
FIELD_ORDER = [
    "unitDesignator",
    "unitNumber",
    "houseNumber",
    "streetPreDirection",
    "streetName",
    "streetTypeCode",
    "streetDirection",
    "cityQuadrant",
    "cityTownName",
    "province",
    "lsd",
    "lsdQuadrant",
    "quarterSectionCode",
    "section",
    "township",
    "range",
    "meridian",
    "ruralHouseNumber",
    "legalLot",
    "lotRangeId",
    "block",
    "governmentPlanId",
    "addressPreRoadNumber",
    "addressRoadType",
    "addressPostRoadNumber",
    "areaName",
    "postalCode",
]

# RULE_MATRIX[combination][field] -> FieldRule
RULE_MATRIX: dict[str, dict[str, FieldRule]] = {
    "URBAN_STREET": {
        "unitDesignator": FieldRule.OPTIONAL,
        "unitNumber": FieldRule.OPTIONAL,
        "houseNumber": FieldRule.REQUIRED,
        "streetPreDirection": FieldRule.OPTIONAL,
        "streetName": FieldRule.REQUIRED,
        "streetTypeCode": FieldRule.OPTIONAL,
        "streetDirection": FieldRule.OPTIONAL,
        "cityQuadrant": FieldRule.OPTIONAL,
        "cityTownName": FieldRule.REQUIRED,
        "province": FieldRule.REQUIRED,
        "lsd": FieldRule.NA,
        "lsdQuadrant": FieldRule.NA,
        "quarterSectionCode": FieldRule.NA,
        "section": FieldRule.NA,
        "township": FieldRule.NA,
        "range": FieldRule.NA,
        "meridian": FieldRule.NA,
        "ruralHouseNumber": FieldRule.NA,
        "legalLot": FieldRule.OPTIONAL,
        "lotRangeId": FieldRule.NA,
        "block": FieldRule.OPTIONAL,
        "governmentPlanId": FieldRule.OPTIONAL,
        "addressPreRoadNumber": FieldRule.NOT_ALLOWED,
        "addressRoadType": FieldRule.NOT_ALLOWED,
        "addressPostRoadNumber": FieldRule.NOT_ALLOWED,
        "areaName": FieldRule.NA,
        "postalCode": FieldRule.OPTIONAL,
    },
    "LLD_ATS_QUARTER": {
        "unitDesignator": FieldRule.NA,
        "unitNumber": FieldRule.NA,
        "houseNumber": FieldRule.NA,
        "streetPreDirection": FieldRule.NA,
        "streetName": FieldRule.NA,
        "streetTypeCode": FieldRule.NA,
        "streetDirection": FieldRule.NA,
        "cityQuadrant": FieldRule.NA,
        "cityTownName": FieldRule.OPTIONAL,
        "province": FieldRule.REQUIRED,
        "lsd": FieldRule.NOT_ALLOWED,
        "lsdQuadrant": FieldRule.NOT_ALLOWED,
        "quarterSectionCode": FieldRule.REQUIRED,
        "section": FieldRule.REQUIRED,
        "township": FieldRule.REQUIRED,
        "range": FieldRule.REQUIRED,
        "meridian": FieldRule.REQUIRED,
        "ruralHouseNumber": FieldRule.OPTIONAL,
        "legalLot": FieldRule.OPTIONAL,
        "lotRangeId": FieldRule.NOT_ALLOWED,
        "block": FieldRule.OPTIONAL,
        "governmentPlanId": FieldRule.OPTIONAL,
        "addressPreRoadNumber": FieldRule.NA,
        "addressRoadType": FieldRule.NA,
        "addressPostRoadNumber": FieldRule.NA,
        "areaName": FieldRule.OPTIONAL,
        "postalCode": FieldRule.NA,
    },
    "LLD_ATS_LSD": {
        "unitDesignator": FieldRule.NA,
        "unitNumber": FieldRule.NA,
        "houseNumber": FieldRule.NA,
        "streetPreDirection": FieldRule.NA,
        "streetName": FieldRule.NA,
        "streetTypeCode": FieldRule.NA,
        "streetDirection": FieldRule.NA,
        "cityQuadrant": FieldRule.NA,
        "cityTownName": FieldRule.NOT_ALLOWED,
        "province": FieldRule.REQUIRED,
        "lsd": FieldRule.REQUIRED,
        "lsdQuadrant": FieldRule.OPTIONAL,
        "quarterSectionCode": FieldRule.NOT_ALLOWED,
        "section": FieldRule.REQUIRED,
        "township": FieldRule.REQUIRED,
        "range": FieldRule.REQUIRED,
        "meridian": FieldRule.REQUIRED,
        "ruralHouseNumber": FieldRule.NOT_ALLOWED,
        "legalLot": FieldRule.NOT_ALLOWED,
        "lotRangeId": FieldRule.NOT_ALLOWED,
        "block": FieldRule.NOT_ALLOWED,
        "governmentPlanId": FieldRule.NOT_ALLOWED,
        "addressPreRoadNumber": FieldRule.NA,
        "addressRoadType": FieldRule.NA,
        "addressPostRoadNumber": FieldRule.NA,
        "areaName": FieldRule.OPTIONAL,
        "postalCode": FieldRule.NA,
    },
    "LOT_BLOCK_PLAN": {
        "unitDesignator": FieldRule.NA,
        "unitNumber": FieldRule.NA,
        "houseNumber": FieldRule.NA,
        "streetPreDirection": FieldRule.NA,
        "streetName": FieldRule.NA,
        "streetTypeCode": FieldRule.NA,
        "streetDirection": FieldRule.NA,
        "cityQuadrant": FieldRule.NA,
        "cityTownName": FieldRule.REQUIRED,
        "province": FieldRule.REQUIRED,
        "lsd": FieldRule.NOT_ALLOWED,
        "lsdQuadrant": FieldRule.NOT_ALLOWED,
        "quarterSectionCode": FieldRule.NOT_ALLOWED,
        "section": FieldRule.NOT_ALLOWED,
        "township": FieldRule.NOT_ALLOWED,
        "range": FieldRule.NOT_ALLOWED,
        "meridian": FieldRule.NOT_ALLOWED,
        "ruralHouseNumber": FieldRule.NOT_ALLOWED,
        "legalLot": FieldRule.REQUIRED,
        "lotRangeId": FieldRule.OPTIONAL,
        "block": FieldRule.OPTIONAL,
        "governmentPlanId": FieldRule.OPTIONAL,
        "addressPreRoadNumber": FieldRule.NA,
        "addressRoadType": FieldRule.NA,
        "addressPostRoadNumber": FieldRule.NA,
        "areaName": FieldRule.OPTIONAL,
        "postalCode": FieldRule.NA,
    },
    "RURAL_ROAD": {
        "unitDesignator": FieldRule.NOT_ALLOWED,
        "unitNumber": FieldRule.NOT_ALLOWED,
        "houseNumber": FieldRule.NOT_ALLOWED,
        "streetPreDirection": FieldRule.NOT_ALLOWED,
        "streetName": FieldRule.NOT_ALLOWED,
        "streetTypeCode": FieldRule.NOT_ALLOWED,
        "streetDirection": FieldRule.NOT_ALLOWED,
        "cityQuadrant": FieldRule.NOT_ALLOWED,
        "cityTownName": FieldRule.NOT_ALLOWED,
        "province": FieldRule.REQUIRED,
        "lsd": FieldRule.NOT_ALLOWED,
        "lsdQuadrant": FieldRule.NOT_ALLOWED,
        "quarterSectionCode": FieldRule.OPTIONAL,
        "section": FieldRule.OPTIONAL,
        "township": FieldRule.OPTIONAL,
        "range": FieldRule.OPTIONAL,
        "meridian": FieldRule.OPTIONAL,
        "ruralHouseNumber": FieldRule.OPTIONAL,
        "legalLot": FieldRule.OPTIONAL,
        "lotRangeId": FieldRule.NOT_ALLOWED,
        "block": FieldRule.OPTIONAL,
        "governmentPlanId": FieldRule.OPTIONAL,
        "addressPreRoadNumber": FieldRule.REQUIRED,
        "addressRoadType": FieldRule.REQUIRED,
        "addressPostRoadNumber": FieldRule.REQUIRED,
        "areaName": FieldRule.OPTIONAL,
        "postalCode": FieldRule.OPTIONAL,
    },
    "RURAL_STREET": {
        "unitDesignator": FieldRule.OPTIONAL,
        "unitNumber": FieldRule.OPTIONAL,
        "houseNumber": FieldRule.OPTIONAL,
        "streetPreDirection": FieldRule.REQUIRED,
        "streetName": FieldRule.REQUIRED,
        "streetTypeCode": FieldRule.REQUIRED,
        "streetDirection": FieldRule.OPTIONAL,
        "cityQuadrant": FieldRule.OPTIONAL,
        "cityTownName": FieldRule.OPTIONAL,
        "province": FieldRule.REQUIRED,
        "lsd": FieldRule.NOT_ALLOWED,
        "lsdQuadrant": FieldRule.NOT_ALLOWED,
        "quarterSectionCode": FieldRule.REQUIRED,
        "section": FieldRule.REQUIRED,
        "township": FieldRule.REQUIRED,
        "range": FieldRule.REQUIRED,
        "meridian": FieldRule.REQUIRED,
        "ruralHouseNumber": FieldRule.OPTIONAL,
        "legalLot": FieldRule.OPTIONAL,
        "lotRangeId": FieldRule.NOT_ALLOWED,
        "block": FieldRule.OPTIONAL,
        "governmentPlanId": FieldRule.OPTIONAL,
        "addressPreRoadNumber": FieldRule.NOT_ALLOWED,
        "addressRoadType": FieldRule.NOT_ALLOWED,
        "addressPostRoadNumber": FieldRule.NOT_ALLOWED,
        "areaName": FieldRule.OPTIONAL,
        "postalCode": FieldRule.OPTIONAL,
    },
}
