import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import aiofiles
from datetime import datetime
import subprocess
import json
from PIL import Image
import asyncio
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/songs",
    tags=["songs"]
)

UPLOAD_DIR = "uploads/songs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

CHUNK_SIZE = 1024 * 1024  # 1MB chunks


async def save_image_file(file: UploadFile, folder: str = "covers") -> str:
    """Save uploaded image file"""
    if not os.path.exists(f"uploads/{folder}"):
        os.makedirs(f"uploads/{folder}")

    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = f"uploads/{folder}/{filename}"

    # Save and resize image
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Resize image to 300x300 for covers
    try:
        with Image.open(file_path) as img:
            img = img.convert('RGB')  # Convert to RGB if needed
            img = img.resize((300, 300), Image.Resampling.LANCZOS)
            img.save(file_path, "JPEG", quality=85)
    except Exception as e:
        print(f"Image processing failed: {e}")

    return file_path


async def save_upload_file(upload_file: UploadFile) -> tuple[str, int]:
    """Save uploaded file and return file path and duration"""
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{upload_file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save file with proper buffering
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            # Read and write in chunks to avoid memory issues
            await upload_file.seek(0)  # Reset file pointer
            while chunk := await upload_file.read(8192):  # 8KB chunks
                await out_file.write(chunk)

        # Ensure file is fully written
        await asyncio.sleep(0.2)

        print(f"File saved: {file_path} ({os.path.getsize(file_path)} bytes)")

    except Exception as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Validate file exists and has content
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        raise HTTPException(status_code=500, detail="File was not saved correctly")

    # Get duration with multiple fallback methods
    duration = await try_ffprobe_duration(file_path)

    if duration == 0:
        print(f"Warning: Could not determine duration for {filename}")
    else:
        print(f"Duration: {duration} seconds for {filename}")

    return file_path, duration

async def try_ffprobe_duration(file_path: str) -> int:
    """Try to get duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', file_path
        ]

        # Run in thread pool to avoid blocking
        def run_ffprobe():
            return subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        result = await asyncio.get_event_loop().run_in_executor(None, run_ffprobe)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration_str = data.get('format', {}).get('duration')
            if duration_str:
                duration = int(float(duration_str))
                print(f"ffprobe: {duration} seconds")
                return duration
        else:
            print(f"ffprobe error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("ffprobe timed out")
    except FileNotFoundError:
        print("ffprobe not found - install ffmpeg")
    except Exception as e:
        print(f"ffprobe failed: {e}")

    return 0

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


async def validate_audio_file(file_path: str) -> bool:
    """Validate that the file is actually an audio file"""
    try:
        # Check file size
        if os.path.getsize(file_path) < 1000:  # Less than 1KB is suspicious
            print(f"File too small: {os.path.getsize(file_path)} bytes")
            return False

        # Try to read first few bytes to check for audio headers
        with open(file_path, 'rb') as f:
            header = f.read(16)

            # Check for common audio file headers
            audio_headers = [
                b'ID3',  # MP3 with ID3
                b'\xff\xfb',  # MP3
                b'\xff\xfa',  # MP3
                b'fLaC',  # FLAC
                b'OggS',  # OGG
                b'\x00\x00\x00\x20ftypM4A',  # M4A
            ]

            for audio_header in audio_headers:
                if header.startswith(audio_header):
                    print(f"Valid audio header found: {audio_header}")
                    return True

        print("No valid audio header found")
        return False

    except Exception as e:
        print(f"File validation error: {e}")
        return False


# Update the create_song endpoint:
@router.post("/", response_model=schemas.Song)
async def create_song(
        title: str = Form(...),
        album_id: Optional[int] = Form(None),
        genre_ids: Optional[List[int]] = Form([]),
        file: UploadFile = File(...),
        cover: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Create a new song with file upload"""
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can create songs"
        )

    # Validate file type and size
    if not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an audio file, got: {file.content_type}"
        )

    cover_path = None
    if cover and cover.filename:
        if not cover.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail=f"Cover must be an image file, got: {cover.content_type}"
            )
        cover_path = await save_image_file(cover, "song_covers")

    # Check file size (e.g., max 50MB)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large (max 50MB)"
        )

    if cover and cover.size and cover.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Cover image too large (max 5MB)"
        )

    print(f"Uploading: {file.filename} ({file.content_type}, {file.size} bytes)")

    # Save file and get duration
    file_path, duration = await save_upload_file(file)

    # Validate the saved file
    if not await validate_audio_file(file_path):
        os.remove(file_path)  # Clean up
        raise HTTPException(
            status_code=400,
            detail="Invalid audio file format"
        )

    # Create song record
    db_song = models.Song(
        title=title,
        duration=duration,
        file_path=file_path,
        cover_image=cover_path,
        album_id=album_id,
        creator_id=current_user.id
    )
    db.add(db_song)
    db.commit()
    db.refresh(db_song)

    print(f"Song created: id={db_song.id}, duration={db_song.duration}")

    # Add genres if provided
    if genre_ids:
        for genre_id in genre_ids:
            genre = db.query(models.Genre).filter(models.Genre.id == genre_id).first()
            if genre:
                db_song.genres.append(genre)
        db.commit()
        db.refresh(db_song)

    return db_song


@router.get("/{song_id}/cover")
async def get_song_cover(
        song_id: int,
        db: Session = Depends(get_db)
):
    """Get song cover image"""
    song = db.query(models.Song).filter(models.Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if song.cover_image and os.path.exists(song.cover_image):
        return FileResponse(song.cover_image)

    if song.album_id:
        album = db.query(models.Album).filter(models.Album.id == song.album_id).first()
        if album and album.cover_image and os.path.exists(album.cover_image):
            return FileResponse(album.cover_image)

    # Return 404 if no cover - client will handle fallback
    raise HTTPException(status_code=404, detail="Song cover not found")

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
    cover: Optional[UploadFile] = File(None),
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

    if cover and cover.filename:
        old_cover_path = db_song.cover_image
        cover_path = await save_image_file(cover, "song_covers")
        db_song.cover_image = cover_path

        # Remove old cover
        if old_cover_path and os.path.exists(old_cover_path):
            os.remove(old_cover_path)

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

@router.post("/check-likes")
def check_multiple_likes(
    song_ids: List[int],
    current_user: models.User = Depends(auth.get_current_active_user)
):
    liked_songs_ids = {song.id for song in current_user.liked_songs}
    return {song_id: song_id in liked_songs_ids for song_id in song_ids}

def add_like_count(song):
    song.like_count = len(song.liked_by)
    return song