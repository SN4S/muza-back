from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import aiofiles
from datetime import datetime
import mutagen
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/songs",
    tags=["songs"]
)

UPLOAD_DIR = "uploads/songs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

CHUNK_SIZE = 1024 * 1024  # 1MB chunks

async def save_upload_file(upload_file: UploadFile) -> tuple[str, int]:
    """Save uploaded file and return file path and duration"""
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{upload_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await upload_file.read()
        await out_file.write(content)
    
    # Get duration using mutagen
    audio = mutagen.File(file_path)
    duration = int(audio.info.length) if audio else 0
    
    return file_path, duration

async def stream_file(file_path: str, start: int = 0, end: Optional[int] = None):
    """Stream file in chunks"""
    async with aiofiles.open(file_path, 'rb') as file:
        await file.seek(start)
        while True:
            if end is not None and start >= end:
                break
            chunk = await file.read(min(CHUNK_SIZE, end - start if end is not None else CHUNK_SIZE))
            if not chunk:
                break
            start += len(chunk)
            yield chunk

@router.post("/", response_model=schemas.Song)
async def create_song(
    title: str = Form(...),
    album_id: Optional[int] = Form(None),
    genre_ids: Optional[List[int]] = Form([]),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Create a new song with file upload"""
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can create songs"
        )
    
    # Validate file type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an audio file"
        )
    
    # Save file and get duration
    file_path, duration = await save_upload_file(file)
    
    # Create song record
    db_song = models.Song(
        title=title,
        duration=duration,
        file_path=file_path,
        album_id=album_id,
        creator_id=current_user.id
    )
    db.add(db_song)
    db.commit()
    db.refresh(db_song)
    
    # Add genres if provided
    if genre_ids:
        for genre_id in genre_ids:
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
async def update_song(
    song_id: int,
    title: Optional[str] = Form(None),
    album_id: Optional[int] = Form(None),
    genre_ids: Optional[List[int]] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if db_song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if db_song.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this song")
    
    # Update basic fields
    if title is not None:
        db_song.title = title
    if album_id is not None:
        db_song.album_id = album_id
    
    # Handle file upload if provided
    if file is not None:
        if not file.content_type.startswith('audio/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an audio file"
            )
        
        # Delete old file
        if os.path.exists(db_song.file_path):
            os.remove(db_song.file_path)
        
        # Save new file
        file_path, duration = await save_upload_file(file)
        db_song.file_path = file_path
        db_song.duration = duration
    
    # Update genres if provided
    if genre_ids is not None:
        db_song.genres = []
        if genre_ids:  # Only process if the list is not empty
            for genre_id in genre_ids:
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
    
    # Delete the file
    if os.path.exists(db_song.file_path):
        os.remove(db_song.file_path)
    
    db.delete(db_song)
    db.commit()
    return {"message": "Song deleted successfully"}

@router.get("/{song_id}/stream")
async def stream_song(
    song_id: int,
    range: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Stream a song with support for range requests"""
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if not os.path.exists(song.file_path):
        raise HTTPException(status_code=404, detail="Song file not found")
    
    file_size = os.path.getsize(song.file_path)
    start = 0
    end = file_size - 1
    
    # Handle range request
    if range:
        try:
            range_header = range.replace('bytes=', '').split('-')
            start = int(range_header[0])
            if range_header[1]:
                end = int(range_header[1])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid range header")
    
    # Get file extension for content type
    file_ext = os.path.splitext(song.file_path)[1].lower()
    content_type = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.flac': 'audio/flac'
    }.get(file_ext, 'audio/mpeg')
    
    # Create response headers
    headers = {
        'Accept-Ranges': 'bytes',
        'Content-Type': content_type,
        'Content-Length': str(end - start + 1),
        'Content-Range': f'bytes {start}-{end}/{file_size}'
    }
    
    return StreamingResponse(
        stream_file(song.file_path, start, end + 1),
        headers=headers,
        media_type=content_type
    )

@router.get("/{song_id}/info")
def get_song_info(
    song_id: int,
    db: Session = Depends(get_db)
):
    """Get song file information"""
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    
    if not os.path.exists(song.file_path):
        raise HTTPException(status_code=404, detail="Song file not found")
    
    file_size = os.path.getsize(song.file_path)
    file_ext = os.path.splitext(song.file_path)[1].lower()
    content_type = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.flac': 'audio/flac'
    }.get(file_ext, 'audio/mpeg')
    
    return {
        "id": song.id,
        "title": song.title,
        "duration": song.duration,
        "file_size": file_size,
        "content_type": content_type,
        "file_path": song.file_path
    }


@router.post("/{song_id}/like")
def like_song(
        song_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if song in current_user.liked_songs:
        raise HTTPException(status_code=400, detail="Song already liked")

    current_user.liked_songs.append(song)
    song.like_count += 1  # Match the field name
    db.commit()
    return {"message": "Song liked successfully"}


@router.delete("/{song_id}/like")
def unlike_song(
        song_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if song not in current_user.liked_songs:
        raise HTTPException(status_code=400, detail="Song not liked")

    current_user.liked_songs.remove(song)
    song.like_count = max(0, song.like_count - 1)  # Match the field name
    db.commit()
    return {"message": "Song unliked successfully"}

@router.get("/{song_id}/is-liked")
def check_if_song_liked(
        song_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    is_liked = song in current_user.liked_songs
    return {"is_liked": is_liked}

def add_like_count(song):
    song.like_count = len(song.liked_by)
    return song