from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.get("/me", response_model=schemas.User)
def get_current_user(
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get current user's profile"""
    return current_user

@router.put("/me", response_model=schemas.User)
def update_current_user(
    user_update: schemas.UserBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Update current user's profile"""
    # Check if username is being changed and if it's already taken
    if user_update.username != current_user.username:
        existing_user = db.query(models.User).filter(
            models.User.username == user_update.username
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
    
    # Check if email is being changed and if it's already taken
    if user_update.email != current_user.email:
        existing_user = db.query(models.User).filter(
            models.User.email == user_update.email
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already taken"
            )
    
    # Update user fields
    for key, value in user_update.dict().items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me/songs", response_model=List[schemas.Song])
def get_current_user_songs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get current user's songs"""
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can have songs"
        )
    songs = db.query(models.Song).filter(
        models.Song.creator_id == current_user.id
    ).offset(skip).limit(limit).all()
    return songs

@router.get("/me/albums", response_model=List[schemas.Album])
def get_current_user_albums(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get current user's albums"""
    if not current_user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="Only artists can have albums"
        )
    albums = db.query(models.Album).filter(
        models.Album.creator_id == current_user.id
    ).offset(skip).limit(limit).all()
    return albums

@router.get("/me/playlists", response_model=List[schemas.Playlist])
def get_current_user_playlists(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get current user's playlists"""
    playlists = db.query(models.Playlist).filter(
        models.Playlist.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return playlists

@router.get("/me/liked-songs", response_model=List[schemas.Song])
def get_current_user_liked_songs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get current user's liked songs"""
    songs = current_user.liked_songs[skip:skip + limit]
    return songs

@router.get("/{user_id}", response_model=schemas.UserNested)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific user's public profile"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/{user_id}/songs", response_model=List[schemas.Song])
def get_user_songs(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get a specific user's songs"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="This user is not an artist"
        )
    
    songs = db.query(models.Song).filter(
        models.Song.creator_id == user_id
    ).offset(skip).limit(limit).all()
    return songs

@router.get("/{user_id}/albums", response_model=List[schemas.Album])
def get_user_albums(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get a specific user's albums"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_artist:
        raise HTTPException(
            status_code=403,
            detail="This user is not an artist"
        )
    
    albums = db.query(models.Album).filter(
        models.Album.creator_id == user_id
    ).offset(skip).limit(limit).all()
    return albums 