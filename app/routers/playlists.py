from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/playlists",
    tags=["playlists"]
)

@router.post("/", response_model=schemas.Playlist)
def create_playlist(
    playlist: schemas.PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_playlist = models.Playlist(**playlist.dict(), owner_id=current_user.id)
    db.add(db_playlist)
    db.commit()
    db.refresh(db_playlist)
    return db_playlist

@router.get("/", response_model=List[schemas.Playlist])
def get_playlists(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    playlists = db.query(models.Playlist).filter(
        models.Playlist.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return playlists

@router.get("/{playlist_id}", response_model=schemas.Playlist)
def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.owner_id == current_user.id
    ).first()
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist

@router.put("/{playlist_id}", response_model=schemas.Playlist)
def update_playlist(
    playlist_id: int,
    playlist: schemas.PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.owner_id == current_user.id
    ).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    for key, value in playlist.dict().items():
        setattr(db_playlist, key, value)
    
    db.commit()
    db.refresh(db_playlist)
    return db_playlist

@router.delete("/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.owner_id == current_user.id
    ).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    db.delete(db_playlist)
    db.commit()
    return {"message": "Playlist deleted successfully"}

@router.post("/{playlist_id}/songs/{song_id}")
def add_song_to_playlist(
    playlist_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.owner_id == current_user.id
    ).first()
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if song in playlist.songs:
        raise HTTPException(status_code=400, detail="Song already in playlist")
    
    playlist.songs.append(song)
    db.commit()
    return {"message": "Song added to playlist successfully"}

@router.delete("/{playlist_id}/songs/{song_id}")
def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.owner_id == current_user.id
    ).first()
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if song not in playlist.songs:
        raise HTTPException(status_code=400, detail="Song not in playlist")
    
    playlist.songs.remove(song)
    db.commit()
    return {"message": "Song removed from playlist successfully"} 