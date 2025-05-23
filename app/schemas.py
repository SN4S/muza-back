from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Song schemas
class SongBase(BaseModel):
    title: str
    duration: int
    file_path: str

class SongCreate(SongBase):
    album_id: Optional[int] = None
    artist_id: int
    genre_ids: List[int]

class Song(SongBase):
    id: int
    created_at: datetime
    album_id: Optional[int]
    artist_id: int

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
    songs: List[Song] = []

    class Config:
        from_attributes = True

# Album schemas
class AlbumBase(BaseModel):
    title: str
    release_date: datetime
    cover_image: Optional[str] = None

class AlbumCreate(AlbumBase):
    artist_id: int

class Album(AlbumBase):
    id: int
    artist_id: int
    created_at: datetime
    songs: List[Song] = []

    class Config:
        from_attributes = True

# Artist schemas
class ArtistBase(BaseModel):
    name: str
    bio: Optional[str] = None
    image: Optional[str] = None

class ArtistCreate(ArtistBase):
    pass

class Artist(ArtistBase):
    id: int
    created_at: datetime
    songs: List[Song] = []
    albums: List[Album] = []

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
    songs: List[Song] = []

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 