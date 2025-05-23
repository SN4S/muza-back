from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/albums",
    tags=["albums"]
)

@router.post("/", response_model=schemas.Album)
def create_album(
    album: schemas.AlbumCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Verify artist exists
    artist = db.query(models.Artist).filter(models.Artist.id == album.artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    db_album = models.Album(**album.dict())
    db.add(db_album)
    db.commit()
    db.refresh(db_album)
    return db_album

@router.get("/", response_model=List[schemas.Album])
def get_albums(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    albums = db.query(models.Album).offset(skip).limit(limit).all()
    return albums

@router.get("/{album_id}", response_model=schemas.Album)
def get_album(
    album_id: int,
    db: Session = Depends(get_db)
):
    album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    return album

@router.put("/{album_id}", response_model=schemas.Album)
def update_album(
    album_id: int,
    album: schemas.AlbumCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if db_album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    # Verify artist exists
    artist = db.query(models.Artist).filter(models.Artist.id == album.artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    for key, value in album.dict().items():
        setattr(db_album, key, value)
    
    db.commit()
    db.refresh(db_album)
    return db_album

@router.delete("/{album_id}")
def delete_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if db_album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    db.delete(db_album)
    db.commit()
    return {"message": "Album deleted successfully"}

@router.get("/artist/{artist_id}", response_model=List[schemas.Album])
def get_artist_albums(
    artist_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Verify artist exists
    artist = db.query(models.Artist).filter(models.Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    albums = db.query(models.Album).filter(
        models.Album.artist_id == artist_id
    ).offset(skip).limit(limit).all()
    return albums 