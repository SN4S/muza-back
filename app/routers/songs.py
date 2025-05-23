from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/songs",
    tags=["songs"]
)

@router.post("/", response_model=schemas.Song)
def create_song(
    song: schemas.SongCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can create songs"
        )
    
    db_song = models.Song(
        **song.dict(exclude={'genre_ids'}),
        creator_id=current_user.id
    )
    db.add(db_song)
    db.commit()
    db.refresh(db_song)
    
    # Add genres
    for genre_id in song.genre_ids:
        genre = db.query(models.Genre).filter(models.Genre.id == genre_id).first()
        if genre:
            db_song.genres.append(genre)
    
    db.commit()
    db.refresh(db_song)
    return db_song

@router.get("/", response_model=List[schemas.Song])
def get_songs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    songs = db.query(models.Song).offset(skip).limit(limit).all()
    return songs

@router.get("/{song_id}", response_model=schemas.Song)
def get_song(
    song_id: int,
    db: Session = Depends(get_db)
):
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    return song

@router.put("/{song_id}", response_model=schemas.Song)
def update_song(
    song_id: int,
    song: schemas.SongCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if db_song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if db_song.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this song")
    
    for key, value in song.dict(exclude={'genre_ids'}).items():
        setattr(db_song, key, value)
    
    # Update genres
    db_song.genres = []
    for genre_id in song.genre_ids:
        genre = db.query(models.Genre).filter(models.Genre.id == genre_id).first()
        if genre:
            db_song.genres.append(genre)
    
    db.commit()
    db.refresh(db_song)
    return db_song

@router.delete("/{song_id}")
def delete_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if db_song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if db_song.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this song")
    
    db.delete(db_song)
    db.commit()
    return {"message": "Song deleted successfully"} 