from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from PIL import Image
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# Create uploads directory for user images
UPLOAD_DIR = "uploads/user_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_user_image(file: UploadFile) -> str:
    """Save uploaded user image and return file path"""
    try:
        print(f"DEBUG save_user_image: Starting with file {file.filename}")

        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp','image/*']
        print(f"DEBUG save_user_image: Content type is {file.content_type}")
        if file.content_type not in allowed_types:
            print(f"DEBUG save_user_image: Invalid content type")
            raise HTTPException(
                status_code=400,
                detail="Only JPEG, PNG, and WebP images are allowed"
            )

        # Check file size (max 5MB)
        print(f"DEBUG save_user_image: Reading file content...")
        file_content = await file.read()
        print(f"DEBUG save_user_image: File size is {len(file_content)} bytes")
        if len(file_content) > 5 * 1024 * 1024:  # 5MB
            print(f"DEBUG save_user_image: File too large")
            raise HTTPException(
                status_code=400,
                detail="Image file too large. Maximum size is 5MB"
            )

        # Generate unique filename
        print(f"DEBUG save_user_image: Generating filename...")
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        print(f"DEBUG save_user_image: Will save to {file_path}")

        # Save file
        print(f"DEBUG save_user_image: Writing file...")
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        print(f"DEBUG save_user_image: File written successfully")

        # Resize image to reasonable size (optional)
        print(f"DEBUG save_user_image: Starting image resize...")
        try:
            with Image.open(file_path) as img:
                print(f"DEBUG save_user_image: Image opened, original size: {img.size}")
                # Resize to max 512x512 while maintaining aspect ratio
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                img.save(file_path, optimize=True, quality=85)
                print(f"DEBUG save_user_image: Image resized and saved")
        except Exception as e:
            print(f"DEBUG save_user_image: Image processing failed but continuing: {e}")
            # If image processing fails, keep original
            pass

        print(f"DEBUG save_user_image: Returning path {file_path}")
        return file_path

    except HTTPException:
        print(f"DEBUG save_user_image: HTTPException raised")
        raise
    except Exception as e:
        print(f"DEBUG save_user_image: Unexpected error: {e}")
        raise HTTPException(status_code=400, detail=f"Image save failed: {str(e)}")

@router.get("/me", response_model=schemas.User)
def get_current_user(
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Get current user's profile"""
    return current_user


@router.put("/me", response_model=schemas.User)
async def update_current_user(
        username: str = Form(...),
        email: str = Form(...),
        bio: Optional[str] = Form(None),
        is_artist: bool = Form(False),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Update current user's profile with optional image upload"""

    # DEBUG: Print what we received
    print(f"DEBUG: Received - username: {username}, email: {email}, bio: {bio}, is_artist: {is_artist}")
    if image:
        print(f"DEBUG: Image - filename: {image.filename}, content_type: {image.content_type}")

    try:
        # Check if username is being changed and if it's already taken
        print(f"DEBUG: Checking username change - current: {current_user.username}, new: {username}")
        if username != current_user.username:
            existing_user = db.query(models.User).filter(
                models.User.username == username
            ).first()
            if existing_user:
                print(f"DEBUG: Username already taken by user ID: {existing_user.id}")
                raise HTTPException(
                    status_code=400,
                    detail="Username already taken"
                )

        # Check if email is being changed and if it's already taken
        print(f"DEBUG: Checking email change - current: {current_user.email}, new: {email}")
        if email != current_user.email:
            existing_user = db.query(models.User).filter(
                models.User.email == email
            ).first()
            if existing_user:
                print(f"DEBUG: Email already taken by user ID: {existing_user.id}")
                raise HTTPException(
                    status_code=400,
                    detail="Email already taken"
                )

        # Handle image upload
        image_path = current_user.image  # Keep existing image by default
        if image:
            print(f"DEBUG: Processing image upload...")
            try:
                # Delete old image if it exists
                if current_user.image and os.path.exists(current_user.image):
                    print(f"DEBUG: Deleting old image: {current_user.image}")
                    try:
                        os.remove(current_user.image)
                    except Exception as e:
                        print(f"DEBUG: Could not delete old image: {e}")

                # Save new image
                print(f"DEBUG: Saving new image...")
                image_path = await save_user_image(image)
                print(f"DEBUG: New image saved to: {image_path}")
            except Exception as e:
                print(f"DEBUG: Image processing failed: {e}")
                raise HTTPException(status_code=400, detail=f"Image processing failed: {str(e)}")

        # Update user fields
        print(f"DEBUG: Updating user fields...")
        current_user.username = username
        current_user.email = email
        current_user.bio = bio
        current_user.is_artist = is_artist
        current_user.image = image_path

        print(f"DEBUG: Committing to database...")
        db.commit()
        db.refresh(current_user)
        print(f"DEBUG: Update successful!")
        return current_user

    except HTTPException:
        print(f"DEBUG: HTTPException raised")
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error: {e}")
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")

@router.delete("/me/image")
def delete_user_image(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Delete current user's profile image"""
    if current_user.image:
        # Delete image file
        if os.path.exists(current_user.image):
            try:
                os.remove(current_user.image)
            except:
                pass

        # Update database
        current_user.image = None
        db.commit()

    return {"message": "Image deleted successfully"}


@router.get("/{user_id}/image")
def get_user_image(user_id: int, db: Session = Depends(get_db)):
    """Get user image file"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.image:
        raise HTTPException(status_code=404, detail="Image not found")

    if os.path.exists(user.image):
        return FileResponse(user.image)
    else:
        raise HTTPException(status_code=404, detail="Image file not found")


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
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get public user profile"""
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
    """Get user's public songs"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

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
    """Get user's public albums"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    albums = db.query(models.Album).filter(
        models.Album.creator_id == user_id
    ).offset(skip).limit(limit).all()
    return albums


# Social features
@router.post("/follow/{user_id}", response_model=schemas.FollowResponse)
def follow_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user in current_user.following:
        raise HTTPException(status_code=400, detail="Already following this user")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    current_user.following.append(target_user)
    db.commit()

    return schemas.FollowResponse(
        is_following=True,
        follower_count=len(target_user.followers),
        following_count=len(target_user.following)
    )


@router.delete("/follow/{user_id}", response_model=schemas.FollowResponse)
def unfollow_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user not in current_user.following:
        raise HTTPException(status_code=400, detail="Not following this user")

    current_user.following.remove(target_user)
    db.commit()

    return schemas.FollowResponse(
        is_following=False,
        follower_count=len(target_user.followers),
        following_count=len(target_user.following)
    )


@router.get("/follow/{user_id}/status", response_model=schemas.FollowResponse)
def get_follow_status(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    return schemas.FollowResponse(
        is_following=target_user in current_user.following,
        follower_count=len(target_user.followers),
        following_count=len(target_user.following)
    )


@router.get("/{user_id}/profile", response_model=schemas.UserProfile)
def get_user_profile(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    song_count = db.query(models.Song).filter(models.Song.creator_id == user.id).count()

    return schemas.UserProfile(
        id=user.id,
        username=user.username,
        bio=user.bio,
        image=user.image,
        is_artist=user.is_artist,
        follower_count=len(user.followers),
        following_count=len(user.following),
        song_count=song_count,
        is_following=user in current_user.following
    )


@router.get("/following", response_model=List[schemas.UserProfile])
def get_my_following(
        skip: int = 0,
        limit: int = 50,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    following_users = current_user.following[skip:skip + limit]

    result = []
    for user in following_users:
        song_count = db.query(models.Song).filter(models.Song.creator_id == user.id).count()
        result.append(schemas.UserProfile(
            id=user.id,
            username=user.username,
            bio=user.bio,
            image=user.image,
            is_artist=user.is_artist,
            follower_count=len(user.followers),
            following_count=len(user.following),
            song_count=song_count,
            is_following=True
        ))

    return result


@router.get("/followers", response_model=List[schemas.UserProfile])
def get_my_followers(
        skip: int = 0,
        limit: int = 50,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    followers = current_user.followers[skip:skip + limit]

    result = []
    for user in followers:
        song_count = db.query(models.Song).filter(models.Song.creator_id == user.id).count()
        result.append(schemas.UserProfile(
            id=user.id,
            username=user.username,
            bio=user.bio,
            image=user.image,
            is_artist=user.is_artist,
            follower_count=len(user.followers),
            following_count=len(user.following),
            song_count=song_count,
            is_following=user in current_user.following
        ))

    return result