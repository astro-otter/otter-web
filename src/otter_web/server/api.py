from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy import text

# Importing the models
from ..database.schema import (
    Transient,
    DateReference,
    Classification,
    Coordinate,
    Name,
    NameAlias,
    Photometry,
    Distance,
    Host,
)
from .models import TransientCreate, TransientRead
import re


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)

# Create a SQLite database
DATABASE_URL = "sqlite:///tde_database.db"
engine = create_engine(DATABASE_URL)


# Dependency to get the session
def get_session():
    with Session(engine) as session:
        yield session


@app.post("/transients/", response_model=TransientRead)
def create_transient(
    transient: TransientCreate, session: Session = Depends(get_session)
):
    db_transient = Transient(
        date_references=[
            DateReference(**date_ref.model_dump())
            for date_ref in transient.date_references
        ],
        classifications=[
            Classification(**classification.model_dump())
            for classification in transient.classifications
        ],
        coordinates=[
            Coordinate(**coordinate.model_dump())
            for coordinate in transient.coordinates
        ],
        name=Name(
            default_name=transient.name.default_name,
            aliases=[
                NameAlias(**alias.model_dump()) for alias in transient.name.aliases
            ],
        ),
        photometries=[
            Photometry(**photometry.model_dump())
            for photometry in transient.photometries
        ],
        distances=[
            Distance(**distance.model_dump()) for distance in transient.distances
        ],
        hosts=[Host(**host.model_dump()) for host in transient.hosts],
        schema_version_id=transient.schema_version_id,
    )
    session.add(db_transient)
    session.commit()
    session.refresh(db_transient)
    return db_transient


@app.get("/transients/", response_model=List[TransientRead])
def read_transients(
    skip: int = 0, limit: int = 10, session: Session = Depends(get_session)
):
    print("Got limit of", limit)
    transients = session.exec(select(Transient).offset(skip).limit(limit)).all()
    return transients


@app.get("/transients/{transient_id}", response_model=TransientRead)
def read_transient(transient_id: int, session: Session = Depends(get_session)):
    transient = session.get(Transient, transient_id)
    if not transient:
        raise HTTPException(status_code=404, detail="Transient not found")
    return transient


@app.put("/transients/{transient_id}", response_model=TransientRead)
def update_transient(
    transient_id: int,
    transient: TransientCreate,
    session: Session = Depends(get_session),
):
    db_transient = session.get(Transient, transient_id)
    if not db_transient:
        raise HTTPException(status_code=404, detail="Transient not found")
    db_transient.date_references = [
        DateReference(**date_ref.model_dump()) for date_ref in transient.date_references
    ]
    db_transient.classifications = [
        Classification(**classification.model_dump())
        for classification in transient.classifications
    ]
    db_transient.coordinates = [
        Coordinate(**coordinate.model_dump()) for coordinate in transient.coordinates
    ]
    db_transient.name = Name(
        default_name=transient.name.default_name,
        aliases=[NameAlias(**alias.model_dump()) for alias in transient.name.aliases],
    )
    db_transient.photometries = [
        Photometry(**photometry.model_dump()) for photometry in transient.photometries
    ]
    db_transient.distances = [
        Distance(**distance.model_dump()) for distance in transient.distances
    ]
    db_transient.hosts = [Host(**host.model_dump()) for host in transient.hosts]
    db_transient.schema_version_id = transient.schema_version_id

    session.add(db_transient)
    session.commit()
    session.refresh(db_transient)
    return db_transient


@app.delete("/transients/{transient_id}")
def delete_transient(transient_id: int, session: Session = Depends(get_session)):
    db_transient = session.get(Transient, transient_id)
    if not db_transient:
        raise HTTPException(status_code=404, detail="Transient not found")
    session.delete(db_transient)
    session.commit()
    return {"ok": True}


@app.get("/execute_query/")
def execute_query(sql: str, session: Session = Depends(get_session)):
    # Allow only SELECT statements
    if not re.match(r"^\s*SELECT\s", sql, re.IGNORECASE):
        raise HTTPException(
            status_code=400, detail="Only SELECT statements are allowed"
        )

    try:
        result = session.exec(text(sql))
        result_dicts = [list(row) for row in result]
        return result_dicts
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/recent_transients/{limit}", response_model=List[TransientRead])
def get_recent_transients(limit: int = 10, session: Session = Depends(get_session)):
    stmt = (
        select(Transient)
        .join(DateReference)
        .order_by(DateReference.value.desc())
        .limit(limit)
    )
    transients = session.exec(stmt).all()
    return transients
