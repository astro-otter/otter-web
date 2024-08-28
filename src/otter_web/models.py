from typing import List, Union, Optional
from datetime import datetime
from pydantic import BaseModel
from pydantic import field_validator, validator


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
    value: Union[str, float, int]
    date_format: str
    date_type: str
    default: Optional[bool] = False


class ClassificationCreate(BaseModel):
    object_class: str
    confidence: float
    default: Optional[bool] = False


class CoordinateCreate(BaseModel):
    ra: Optional[Union[str, float]] = None
    dec: Optional[Union[str, float]] = None
    ra_units: Optional[str] = None
    dec_units: Optional[str] = None

    l: Optional[Union[str, float]] = None
    b: Optional[Union[str, float]] = None
    l_units: Optional[str] = None
    b_units: Optional[str] = None
    
    coordinate_type: str
    default: Optional[bool] = False
    
class PhotometryCreate(BaseModel):
    raw: List[float]
    raw_err: Optional[List[float]] = []
    raw_units: Union[str, List[str]]
    filter_key: Union[str, List[str]]
    obs_type: Union[str, List[str]]
    date: Union[str, List[str], float, List[float]]
    date_format: Union[str, List[str]]
    upperlimit: Optional[Union[bool, List[bool]]] = []
    telescope: Optional[Union[str, List[str]]] = []
    corr_k: Optional[Union[bool, List[bool]]] = None
    corr_av: Optional[Union[bool, List[bool]]] = None
    corr_host: Optional[Union[bool, List[bool]]] = None
    corr_hostav: Optional[Union[bool, List[bool]]] = None

    @field_validator(
        "raw_units",
        "raw_err",
        "filter_key",
        "obs_type",
        "date_format",
        "upperlimit",
        "date",
        "telescope"
    )
    def ensure_list(cls, v):
        if not isinstance(v, list):
            return [v]
        return v


class DistanceCreate(BaseModel):
    value: float
    distance_type: str
    unit: Optional[str] = None
    default: Optional[bool] = None


class HostCreate(BaseModel):
    host_name: Optional[str]
    host_ra: Optional[Union[float,str]]
    host_dec: Optional[Union[float,str]]
    host_ra_units: Optional[str]
    host_dec_units: Optional[str]


class TransientCreate(BaseModel):
    date_reference: Optional[List[DateReferenceCreate]] = []
    classification: Optional[List[ClassificationCreate]] = []
    coordinate: List[CoordinateCreate] = []
    name: NameCreate
    photometry: Optional[List[PhotometryCreate]] = []
    distance: Optional[List[DistanceCreate]] = []
    host: Optional[List[HostCreate]] = []

class TransientRead(TransientCreate):
    _id: int
    _key: int
