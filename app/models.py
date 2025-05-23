from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# Association tables for many-to-many relationships
song_playlist = Table(
    'song_playlist',
    Base.metadata,
    Column('song_id', Integer, ForeignKey('songs.id')),
    Column('playlist_id', Integer, ForeignKey('playlists.id'))
)

song_genre = Table(
    'song_genre',
    Base.metadata,
    Column('song_id', Integer, ForeignKey('songs.id')),
    Column('genre_id', Integer, ForeignKey('genres.id'))
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    playlists = relationship("Playlist", back_populates="owner")
    liked_songs = relationship("Song", secondary="user_liked_songs", back_populates="liked_by")

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    duration = Column(Integer)  # Duration in seconds
    file_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    album_id = Column(Integer, ForeignKey("albums.id"))
    artist_id = Column(Integer, ForeignKey("artists.id"))
    
    album = relationship("Album", back_populates="songs")
    artist = relationship("Artist", back_populates="songs")
    playlists = relationship("Playlist", secondary=song_playlist, back_populates="songs")
    genres = relationship("Genre", secondary=song_genre, back_populates="songs")
    liked_by = relationship("User", secondary="user_liked_songs", back_populates="liked_songs")

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="playlists")
    songs = relationship("Song", secondary=song_playlist, back_populates="playlists")

class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    release_date = Column(DateTime(timezone=True))
    cover_image = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    artist_id = Column(Integer, ForeignKey("artists.id"))
    
    artist = relationship("Artist", back_populates="albums")
    songs = relationship("Song", back_populates="album")

class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    bio = Column(Text, nullable=True)
    image = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    songs = relationship("Song", back_populates="artist")
    albums = relationship("Album", back_populates="artist")

class Genre(Base):
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    songs = relationship("Song", secondary=song_genre, back_populates="genres")

# Association table for user liked songs
class UserLikedSongs(Base):
    __tablename__ = "user_liked_songs"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 