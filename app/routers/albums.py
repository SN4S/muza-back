import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from fastapi.responses import FileResponse

from .songs import save_image_file
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/albums",
    tags=["albums"]
)

@router.post("/", response_model=schemas.Album)
async def create_album(
        title: str = Form(...),
        release_date: str = Form(...),
        cover: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Create a new album with optional cover image"""
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can create albums"
        )

    # Validate cover if provided
    cover_path = None
    if cover and cover.filename:
        if not cover.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail=f"Cover must be an image file, got: {cover.content_type}"
            )

        if cover.size and cover.size > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Cover image too large (max 5MB)"
            )

        cover_path = await save_image_file(cover, "album_covers")

    # Parse release date
    try:
        release_datetime = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        )

    # Create album
    db_album = models.Album(
        title=title,
        release_date=release_datetime,
        cover_image=cover_path,
        creator_id=current_user.id
    )
    db.add(db_album)
    db.commit()
    db.refresh(db_album)
    return db_album


@router.get("/{album_id}/cover")
async def get_album_cover(
        album_id: int,
        db: Session = Depends(get_db)
):
    """Get album cover image"""
    album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    if album.cover_image and os.path.exists(album.cover_image):
        return FileResponse(album.cover_image)

    # Return 404 if no cover - client will handle fallback
    raise HTTPException(status_code=404, detail="Album cover not found")

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
async def update_album(
    album_id: int,
    title: Optional[str] = Form(None),
    release_date: Optional[str] = Form(None),
    cover: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if db_album is None:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if db_album.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this album")

    if title:
        db_album.title = title
    if release_date:
        try:
            release_datetime = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
            db_album.release_date = release_datetime
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
            )

        # Update cover if provided
    if cover and cover.filename:
        if not cover.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail=f"Cover must be an image file, got: {cover.content_type}"
            )

        old_cover_path = db_album.cover_image
        cover_path = await save_image_file(cover, "album_covers")
        db_album.cover_image = cover_path

        # Remove old cover
        if old_cover_path and os.path.exists(old_cover_path):
            os.remove(old_cover_path)

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


@router.post("/{album_id}/like")
async def like_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    current_user.liked_albums.append(album)
    album.like_count += 1
    db.commit()
    return {"message": "Album liked successfully"}


@router.delete("/{album_id}/like")
async def unlike_album(
        album_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    current_user.liked_albums.remove(album)
    album.like_count = max(0, album.like_count - 1)  # Match the field name
    db.commit()
    return {"message": "Album unliked successfully"}

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