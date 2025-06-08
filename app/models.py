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

user_follows = Table(
    'user_follows',
    Base.metadata,
    Column('follower_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('following_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_artist = Column(Boolean, default=False)
    bio = Column(Text, nullable=True)
    image = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    playlists = relationship("Playlist", back_populates="owner")
    liked_songs = relationship("Song", secondary="user_liked_songs", back_populates="liked_by")
    songs = relationship("Song", back_populates="creator")
    albums = relationship("Album", back_populates="creator")
    following = relationship(
        "User",
        secondary=user_follows,
        primaryjoin=id == user_follows.c.follower_id,
        secondaryjoin=id == user_follows.c.following_id,
        back_populates="followers"
    )

    followers = relationship(
        "User",
        secondary=user_follows,
        primaryjoin=id == user_follows.c.following_id,
        secondaryjoin=id == user_follows.c.follower_id,
        back_populates="following"
    )

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    duration = Column(Integer)  # Duration in seconds
    file_path = Column(String)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    album_id = Column(Integer, ForeignKey("albums.id"))
    creator_id = Column(Integer, ForeignKey("users.id"))
    
    album = relationship("Album", back_populates="songs")
    creator = relationship("User", back_populates="songs")
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
    
    creator_id = Column(Integer, ForeignKey("users.id"))
    
    creator = relationship("User", back_populates="albums")
    songs = relationship("Song", back_populates="album")

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