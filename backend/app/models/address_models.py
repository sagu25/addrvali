from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AddressType(str, Enum):
    CIVIC = "Civic"
    LEGAL = "Legal"
    RURAL = "Rural"


class AddressCombination(str, Enum):
    URBAN_STREET = "UrbanStreet"
    LLD_ATS_QUARTER = "LLD_ATS_Quarter"
    LLD_ATS_LSD = "LLD_ATS_LSD"
    LOT_BLOCK_PLAN = "LotBlockPlan"
    RURAL_ROAD = "RuralRoad"
    RURAL_STREET = "RuralStreet"


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationStatus(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class BulkAddressCsvRow(BaseModel):
    batchId: Optional[str] = None
    rowId: Optional[int] = None

    objectId: Optional[int] = None
    servicePointKey: Optional[str] = None
    distributionSiteId: Optional[str] = None

    addressType: AddressType
    addressCombination: Optional[AddressCombination] = None

    unitDesignator: Optional[str] = None
    unitNumber: Optional[str] = None

    houseNumber: Optional[str] = None
    streetPreDirection: Optional[str] = None
    streetName: Optional[str] = None
    streetTypeCode: Optional[str] = None
    streetDirection: Optional[str] = None
    cityQuadrant: Optional[str] = None

    cityTownName: Optional[str] = None
    province: Optional[str] = None

    lsd: Optional[str] = None
    lsdQuadrant: Optional[str] = None
    quarterSectionCode: Optional[str] = None
    section: Optional[str] = None
    township: Optional[str] = None
    range: Optional[str] = None
    meridian: Optional[str] = None
    ruralHouseNumber: Optional[str] = None

    legalLot: Optional[str] = None
    lotRangeId: Optional[str] = None
    block: Optional[str] = None
    governmentPlanId: Optional[str] = None

    addressPreRoadNumber: Optional[str] = None
    addressRoadType: Optional[str] = None
    addressPostRoadNumber: Optional[str] = None

    areaName: Optional[str] = None
    postalCode: Optional[str] = None

    changedBy: Optional[str] = None

    @field_validator("addressType", mode="before")
    @classmethod
    def normalise_address_type(cls, value):
        if value is None:
            raise ValueError("addressType is required.")
        if isinstance(value, AddressType):
            return value
        value_str = str(value).strip().lower()
        if value_str in ["civil", "civic", "urban"]:
            return AddressType.CIVIC
        if value_str == "legal":
            return AddressType.LEGAL
        if value_str == "rural":
            return AddressType.RURAL
        raise ValueError("addressType must be Civic, Legal, or Rural.")

    @field_validator("province", mode="before")
    @classmethod
    def normalise_province(cls, value):
        if value is None:
            return value
        return str(value).strip().upper()

    @field_validator("postalCode", mode="before")
    @classmethod
    def normalise_postal_code(cls, value):
        if value is None:
            return value
        return str(value).strip().upper().replace(" ", "")

    def populated_fields(self) -> List[str]:
        populated = []
        for field_name, value in self.model_dump().items():
            if value not in [None, ""]:
                populated.append(field_name)
        return populated


class ValidationIssue(BaseModel):
    fieldName: Optional[str] = None
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


class ValidationComponentResult(BaseModel):
    componentName: str
    status: ValidationStatus
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecordValidationResult(BaseModel):
    batchId: Optional[str] = None
    rowId: Optional[int] = None
    objectId: Optional[int] = None
    servicePointKey: Optional[str] = None
    distributionSiteId: Optional[str] = None

    addressType: AddressType
    addressCombination: Optional[AddressCombination] = None

    finalStatus: ValidationStatus

    ruleValidation: ValidationComponentResult
    combinationValidation: Optional[ValidationComponentResult] = None
    geocodeValidation: Optional[ValidationComponentResult] = None
    preDispatchValidation: Optional[ValidationComponentResult] = None

    aiExplanation: Optional[str] = None
    explanationSource: Optional[str] = None  # "azure_openai" | "template"
    suggestedCorrection: Optional[Dict[str, Any]] = None


class BulkAddressValidationResponse(BaseModel):
    batchId: str
    totalRecords: int
    greenCount: int
    amberCount: int
    redCount: int
    results: List[RecordValidationResult]
