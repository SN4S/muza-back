from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/search",
    tags=["search"]
)

@router.get("/songs", response_model=List[schemas.Song])
def search_songs(
    query: str = Query(..., min_length=1),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    songs = db.query(models.Song).filter(
        or_(
            models.Song.title.ilike(f"%{query}%"),
            models.Song.artist.has(models.Artist.name.ilike(f"%{query}%")),
            models.Song.album.has(models.Album.title.ilike(f"%{query}%"))
        )
    ).offset(skip).limit(limit).all()
    return songs

@router.get("/artists", response_model=List[schemas.Artist])
def search_artists(
    query: str = Query(..., min_length=1),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    artists = db.query(models.Artist).filter(
        models.Artist.name.ilike(f"%{query}%")
    ).offset(skip).limit(limit).all()
    return artists

@router.get("/albums", response_model=List[schemas.Album])
def search_albums(
    query: str = Query(..., min_length=1),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    albums = db.query(models.Album).filter(
        or_(
            models.Album.title.ilike(f"%{query}%"),
            models.Album.artist.has(models.Artist.name.ilike(f"%{query}%"))
        )
    ).offset(skip).limit(limit).all()
    return albums

@router.get("/playlists", response_model=List[schemas.Playlist])
def search_playlists(
    query: str = Query(..., min_length=1),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    playlists = db.query(models.Playlist).filter(
        or_(
            models.Playlist.name.ilike(f"%{query}%"),
            models.Playlist.description.ilike(f"%{query}%")
        )
    ).offset(skip).limit(limit).all()
    return playlists

@router.get("/genres", response_model=List[schemas.Genre])
def search_genres(
    query: str = Query(..., min_length=1),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    genres = db.query(models.Genre).filter(
        models.Genre.name.ilike(f"%{query}%")
    ).offset(skip).limit(limit).all()
    return genres 