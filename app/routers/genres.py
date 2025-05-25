from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/genres",
    tags=["genres"]
)


@router.post("/", response_model=schemas.Genre)
def create_genre(
        genre: schemas.GenreCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    # Check if genre already exists
    existing_genre = db.query(models.Genre).filter(models.Genre.name == genre.name).first()
    if existing_genre:
        raise HTTPException(status_code=400, detail="Genre already exists")

    db_genre = models.Genre(**genre.dict())
    db.add(db_genre)
    db.commit()
    db.refresh(db_genre)
    return db_genre


@router.get("/", response_model=List[schemas.Genre])
def get_genres(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    genres = db.query(models.Genre).offset(skip).limit(limit).all()
    return genres


@router.get("/{genre_id}", response_model=schemas.Genre)
def get_genre(
        genre_id: int,
        db: Session = Depends(get_db)
):
    genre = db.query(models.Genre).filter(models.Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre


@router.put("/{genre_id}", response_model=schemas.Genre)
def update_genre(
        genre_id: int,
        genre: schemas.GenreCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    db_genre = db.query(models.Genre).filter(models.Genre.id == genre_id).first()
    if not db_genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    # Check if new name conflicts with existing genre
    if genre.name != db_genre.name:
        existing = db.query(models.Genre).filter(models.Genre.name == genre.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Genre name already exists")

    for key, value in genre.dict().items():
        setattr(db_genre, key, value)

    db.commit()
    db.refresh(db_genre)
    return db_genre


@router.delete("/{genre_id}")
def delete_genre(
        genre_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    db_genre = db.query(models.Genre).filter(models.Genre.id == genre_id).first()
    if not db_genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    db.delete(db_genre)
    db.commit()
    return {"message": "Genre deleted successfully"}


@router.get("/{genre_id}/songs", response_model=List[schemas.Song])
def get_genre_songs(
        genre_id: int,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    genre = db.query(models.Genre).filter(models.Genre.id == genre_id).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    songs = db.query(models.Song).join(models.Song.genres).filter(
        models.Genre.id == genre_id
    ).offset(skip).limit(limit).all()
    return songs