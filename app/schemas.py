from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from fastapi import UploadFile

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    bio: Optional[str] = None
    image: Optional[str] = None
    is_artist: bool = False

class UserCreate(UserBase):
    password: str

# Nested schemas to avoid circular references
class UserNested(BaseModel):
    id: int
    username: str
    bio: Optional[str] = None
    image: Optional[str] = None
    is_artist: bool

    class Config:
        from_attributes = True

class SongNested(BaseModel):
    id: int
    title: str
    duration: int
    file_path: str
    created_at: datetime
    creator: UserNested

    class Config:
        from_attributes = True

class AlbumNested(BaseModel):
    id: int
    title: str
    release_date: datetime
    cover_image: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    songs: List[SongNested] = []
    albums: List[AlbumNested] = []

    class Config:
        from_attributes = True

# Song schemas
class SongBase(BaseModel):
    title: str
    duration: Optional[int] = None  # Will be calculated from the uploaded file

class SongCreate(SongBase):
    album_id: Optional[int] = None
    genre_ids: Optional[List[int]] = []

class SongUpload(SongCreate):
    file: UploadFile

class Song(SongBase):
    id: int
    created_at: datetime
    file_path: str
    album_id: Optional[int]
    creator_id: int
    creator: UserNested
    like_count: int = 0

    class Config:
        from_attributes = True

# Playlist schemas
class PlaylistBase(BaseModel):
    name: str
    description: Optional[str] = None

class PlaylistCreate(PlaylistBase):
    pass

class Playlist(PlaylistBase):
    id: int
    owner_id: int
    created_at: datetime
    songs: List[SongNested] = []

    class Config:
        from_attributes = True

# Album schemas
class AlbumBase(BaseModel):
    title: str
    release_date: datetime
    cover_image: Optional[str] = None

class AlbumCreate(AlbumBase):
    pass

class Album(AlbumBase):
    id: int
    creator_id: int
    created_at: datetime
    songs: List[SongNested] = []
    creator: UserNested

    class Config:
        from_attributes = True

# Genre schemas
class GenreBase(BaseModel):
    name: str
    description: Optional[str] = None

class GenreCreate(GenreBase):
    pass

class Genre(GenreBase):
    id: int
    songs: List[SongNested] = []

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 