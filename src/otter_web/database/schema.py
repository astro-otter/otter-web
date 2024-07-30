from sqlmodel import Field, SQLModel, Relationship, create_engine, Session, Column
from sqlalchemy.dialects.sqlite import JSON
from typing import List, Optional
from datetime import datetime


class Reference(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    human_readable_name: str
    date_references: List["DateReferenceReferenceLink"] = Relationship(
        back_populates="reference"
    )
    classifications: List["ClassificationReferenceLink"] = Relationship(
        back_populates="reference"
    )
    coordinates: List["CoordinateReferenceLink"] = Relationship(
        back_populates="reference"
    )
    name_aliases: List["NameAliasReferenceLink"] = Relationship(
        back_populates="reference"
    )
    photometries: List["PhotometryReferenceLink"] = Relationship(
        back_populates="reference"
    )
    distances: List["DistanceReferenceLink"] = Relationship(back_populates="reference")
    hosts: List["HostReferenceLink"] = Relationship(back_populates="reference")


class FilterAlias(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filter_key: str
    wave_eff: Optional[float] = None
    wave_units: Optional[str] = None
    filter_name: str
    freq_eff: Optional[float] = None
    freq_units: Optional[str] = None
    photometries: List["Photometry"] = Relationship(back_populates="filter_alias")


class DateReference(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: datetime
    date_format: str
    date_type: str
    default: bool
    transient_id: Optional[int] = Field(default=None, foreign_key="transient.id")
    transient: "Transient" = Relationship(back_populates="date_references")
    references: List["DateReferenceReferenceLink"] = Relationship(
        back_populates="date_reference"
    )


class DateReferenceReferenceLink(SQLModel, table=True):
    date_reference_id: Optional[int] = Field(
        default=None, foreign_key="datereference.id", primary_key=True
    )
    reference_id: Optional[int] = Field(
        default=None, foreign_key="reference.id", primary_key=True
    )
    date_reference: DateReference = Relationship(back_populates="references")
    reference: Reference = Relationship(back_populates="date_references")


class Classification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    object_class: str
    confidence: float
    default: bool
    transient_id: Optional[int] = Field(default=None, foreign_key="transient.id")
    transient: "Transient" = Relationship(back_populates="classifications")
    references: List["ClassificationReferenceLink"] = Relationship(
        back_populates="classification"
    )


class ClassificationReferenceLink(SQLModel, table=True):
    classification_id: Optional[int] = Field(
        default=None, foreign_key="classification.id", primary_key=True
    )
    reference_id: Optional[int] = Field(
        default=None, foreign_key="reference.id", primary_key=True
    )
    classification: Classification = Relationship(back_populates="references")
    reference: Reference = Relationship(back_populates="classifications")


class Coordinate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ra: str
    dec: str
    ra_units: str
    dec_units: str
    coordinate_type: str
    default: bool
    transient_id: Optional[int] = Field(default=None, foreign_key="transient.id")
    transient: "Transient" = Relationship(back_populates="coordinates")
    references: List["CoordinateReferenceLink"] = Relationship(
        back_populates="coordinate"
    )


class CoordinateReferenceLink(SQLModel, table=True):
    coordinate_id: Optional[int] = Field(
        default=None, foreign_key="coordinate.id", primary_key=True
    )
    reference_id: Optional[int] = Field(
        default=None, foreign_key="reference.id", primary_key=True
    )
    coordinate: Coordinate = Relationship(back_populates="references")
    reference: Reference = Relationship(back_populates="coordinates")


class NameAlias(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: str
    name_id: Optional[int] = Field(default=None, foreign_key="name.id")
    name: "Name" = Relationship(back_populates="aliases")
    references: List["NameAliasReferenceLink"] = Relationship(
        back_populates="name_alias"
    )


class NameAliasReferenceLink(SQLModel, table=True):
    name_alias_id: Optional[int] = Field(
        default=None, foreign_key="namealias.id", primary_key=True
    )
    reference_id: Optional[int] = Field(
        default=None, foreign_key="reference.id", primary_key=True
    )
    name_alias: NameAlias = Relationship(back_populates="references")
    reference: Reference = Relationship(back_populates="name_aliases")


class Name(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    default_name: str
    transient_id: Optional[int] = Field(default=None, foreign_key="transient.id")
    transient: Optional["Transient"] = Relationship(
        back_populates="name",
        # sa_relationship_kwargs={"foreign_keys": "Name.transient_id"},
    )
    aliases: List[NameAlias] = Relationship(back_populates="name")


class Photometry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    raw: List[float] = Field(sa_column=Column(JSON))
    raw_err: List[float] = Field(sa_column=Column(JSON))
    raw_units: List[str] = Field(sa_column=Column(JSON))
    filter_key: List[str] = Field(sa_column=Column(JSON))
    obs_type: List[str] = Field(sa_column=Column(JSON))
    date: List[str] = Field(sa_column=Column(JSON))
    date_format: List[str] = Field(sa_column=Column(JSON))
    upperlimit: List[bool] = Field(sa_column=Column(JSON))
    telescope: str
    corr_k: Optional[bool] = None
    corr_av: Optional[bool] = None
    corr_host: Optional[bool] = None
    corr_hostav: Optional[bool] = None
    transient_id: Optional[int] = Field(default=None, foreign_key="transient.id")
    transient: "Transient" = Relationship(back_populates="photometries")
    filter_alias_id: Optional[int] = Field(default=None, foreign_key="filteralias.id")
    filter_alias: Optional[FilterAlias] = Relationship(back_populates="photometries")
    references: List["PhotometryReferenceLink"] = Relationship(
        back_populates="photometry"
    )


class PhotometryReferenceLink(SQLModel, table=True):
    photometry_id: Optional[int] = Field(
        default=None, foreign_key="photometry.id", primary_key=True
    )
    reference_id: Optional[int] = Field(
        default=None, foreign_key="reference.id", primary_key=True
    )
    photometry: Photometry = Relationship(back_populates="references")
    reference: Reference = Relationship(back_populates="photometries")


class Distance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: float
    distance_type: str
    unit: Optional[str] = None
    default: bool
    transient_id: Optional[int] = Field(default=None, foreign_key="transient.id")
    transient: "Transient" = Relationship(back_populates="distances")
    references: List["DistanceReferenceLink"] = Relationship(back_populates="distance")


class DistanceReferenceLink(SQLModel, table=True):
    distance_id: Optional[int] = Field(
        default=None, foreign_key="distance.id", primary_key=True
    )
    reference_id: Optional[int] = Field(
        default=None, foreign_key="reference.id", primary_key=True
    )
    distance: Distance = Relationship(back_populates="references")
    reference: Reference = Relationship(back_populates="distances")


class Host(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    host_name: str
    host_ra: float
    host_dec: float
    host_ra_units: str
    host_dec_units: str
    transient_id: Optional[int] = Field(default=None, foreign_key="transient.id")
    transient: "Transient" = Relationship(back_populates="hosts")
    references: List["HostReferenceLink"] = Relationship(back_populates="host")


class HostReferenceLink(SQLModel, table=True):
    host_id: Optional[int] = Field(
        default=None, foreign_key="host.id", primary_key=True
    )
    reference_id: Optional[int] = Field(
        default=None, foreign_key="reference.id", primary_key=True
    )
    host: Host = Relationship(back_populates="references")
    reference: Reference = Relationship(back_populates="hosts")


class SchemaVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: int
    comments: str
    transients: List["Transient"] = Relationship(back_populates="schema_version")


class Transient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date_references: List[DateReference] = Relationship(back_populates="transient")
    classifications: List[Classification] = Relationship(back_populates="transient")
    coordinates: List[Coordinate] = Relationship(back_populates="transient")
    name: Optional[Name] = Relationship(back_populates="transient")
    photometries: List[Photometry] = Relationship(back_populates="transient")
    distances: List[Distance] = Relationship(back_populates="transient")
    hosts: List[Host] = Relationship(back_populates="transient")
    schema_version_id: Optional[int] = Field(
        default=None, foreign_key="schemaversion.id"
    )
    schema_version: SchemaVersion = Relationship(back_populates="transients")
