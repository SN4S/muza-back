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
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can create albums"
        )
    
    db_album = models.Album(**album.dict(), creator_id=current_user.id)
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
    
    if db_album.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this album")
    
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
    
    if db_album.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this album")
    
    db.delete(db_album)
    db.commit()
    return {"message": "Album deleted successfully"}

@router.get("/{album_id}/songs", response_model=List[schemas.Song])
def get_album_songs(
    album_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all songs in an album"""
    album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    songs = db.query(models.Song).filter(
        models.Song.album_id == album_id
    ).offset(skip).limit(limit).all()
    return songs

@router.post("/{album_id}/songs/{song_id}")
def add_song_to_album(
    album_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Add a song to an album"""
    # Check if album exists and user is the creator
    album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if album.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this album")
    
    # Check if song exists and user is the creator
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if song.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to add this song to the album")
    
    # Check if song is already in the album
    if song.album_id == album_id:
        raise HTTPException(status_code=400, detail="Song is already in this album")
    
    # Add song to album
    song.album_id = album_id
    db.commit()
    return {"message": "Song added to album successfully"}

@router.delete("/{album_id}/songs/{song_id}")
def remove_song_from_album(
    album_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Remove a song from an album"""
    # Check if album exists and user is the creator
    album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if album.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this album")
    
    # Check if song exists and is in the album
    song = db.query(models.Song).filter(
        models.Song.id == song_id,
        models.Song.album_id == album_id
    ).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found in this album")
    
    # Remove song from album
    song.album_id = None
    db.commit()
    return {"message": "Song removed from album successfully"}

@router.get("/user/{user_id}", response_model=List[schemas.Album])
def get_user_albums(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    albums = db.query(models.Album).filter(
        models.Album.creator_id == user_id
    ).offset(skip).limit(limit).all()
    return albums 