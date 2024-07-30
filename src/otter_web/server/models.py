from typing import List, Union, Optional
from datetime import datetime
from pydantic import BaseModel
from pydantic import field_validator


class NameAliasCreate(BaseModel):
    value: str


class NameCreate(BaseModel):
    default_name: str
    aliases: List[NameAliasCreate] = []


class ReferenceCreate(BaseModel):
    name: str
    human_readable_name: str


class FilterAliasCreate(BaseModel):
    filter_key: str
    wave_eff: Optional[float] = None
    wave_units: Optional[str] = None
    filter_name: str
    freq_eff: Optional[float] = None
    freq_units: Optional[str] = None


class DateReferenceCreate(BaseModel):
    value: datetime
    date_format: str
    date_type: str
    default: bool


class ClassificationCreate(BaseModel):
    object_class: str
    confidence: float
    default: bool


class CoordinateCreate(BaseModel):
    ra: str
    dec: str
    ra_units: str
    dec_units: str
    coordinate_type: str
    default: bool


class PhotometryCreate(BaseModel):
    raw: List[float]
    raw_err: List[float]
    raw_units: Union[str, List[str]]
    filter_key: Union[str, List[str]]
    obs_type: Union[str, List[str]]
    date: List[str]
    date_format: Union[str, List[str]]
    upperlimit: List[bool]
    telescope: str
    corr_k: Optional[bool] = None
    corr_av: Optional[bool] = None
    corr_host: Optional[bool] = None
    corr_hostav: Optional[bool] = None

    @field_validator(
        "raw_units", "filter_key", "obs_type", "date_format", "upperlimit", "date"
    )
    def ensure_list(cls, v):
        if not isinstance(v, list):
            return [v]
        return v


class DistanceCreate(BaseModel):
    value: float
    distance_type: str
    unit: Optional[str] = None
    default: bool


class HostCreate(BaseModel):
    host_name: str
    host_ra: float
    host_dec: float
    host_ra_units: str
    host_dec_units: str


class TransientCreate(BaseModel):
    date_references: Optional[List[DateReferenceCreate]] = []
    classifications: List[ClassificationCreate] = []
    coordinates: List[CoordinateCreate] = []
    name: NameCreate
    photometries: Optional[List[PhotometryCreate]] = []
    distances: List[DistanceCreate] = []
    hosts: Optional[List[HostCreate]] = []
    schema_version_id: int


class TransientRead(TransientCreate):
    id: int
