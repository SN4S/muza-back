# Music Streaming API

A FastAPI-based music streaming service that allows users to upload, manage, and stream music. The service supports both regular users and artists, with features for managing songs, albums, playlists, and user interactions.

## Project Structure

```
music-streaming-api/
├── app/
│   ├── routers/
│   │   ├── albums.py      # Album management endpoints
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── genres.py      # Genre management endpoints
│   │   ├── playlists.py   # Playlist management endpoints
│   │   ├── songs.py       # Song management endpoints
│   │   └── users.py       # User management endpoints
│   ├── models.py          # SQLAlchemy database models
│   ├── schemas.py         # Pydantic data schemas
│   ├── auth.py           # Authentication utilities
│   └── database.py       # Database configuration
├── uploads/              # Directory for uploaded music files
├── requirements.txt      # Project dependencies
└── main.py              # FastAPI application entry point
```

## Features

### User Management
- User registration and authentication
- Profile management (update bio, image, etc.)
- Artist status for content creators
- Public and private user profiles

### Song Management
- Upload and manage songs
- Add songs to albums
- Categorize songs by genres
- Like/unlike songs
- Stream songs

### Album Management
- Create and manage albums
- Add songs to albums
- Album cover images
- Release date tracking

### Playlist Management
- Create and manage playlists
- Add/remove songs from playlists
- Public and private playlists

### Genre Management
- Create and manage genres
- Categorize songs by genres
- Genre-based search

## API Endpoints

### Authentication
- `POST /auth/token` - Get access token
- `POST /auth/register` - Register new user

### Users
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update current user profile
- `GET /users/me/songs` - Get current user's songs
- `GET /users/me/albums` - Get current user's albums
- `GET /users/me/playlists` - Get current user's playlists
- `GET /users/me/liked-songs` - Get current user's liked songs
- `GET /users/{user_id}` - Get public user profile
- `GET /users/{user_id}/songs` - Get user's songs
- `GET /users/{user_id}/albums` - Get user's albums

### Songs
- `POST /songs/` - Create new song
- `GET /songs/` - List all songs
- `GET /songs/{song_id}` - Get song details
- `PUT /songs/{song_id}` - Update song
- `DELETE /songs/{song_id}` - Delete song

### Albums
- `POST /albums/` - Create new album
- `GET /albums/` - List all albums
- `GET /albums/{album_id}` - Get album details
- `PUT /albums/{album_id}` - Update album
- `DELETE /albums/{album_id}` - Delete album
- `GET /albums/user/{user_id}` - Get user's albums

### Playlists
- `POST /playlists/` - Create new playlist
- `GET /playlists/` - List all playlists
- `GET /playlists/{playlist_id}` - Get playlist details
- `PUT /playlists/{playlist_id}` - Update playlist
- `DELETE /playlists/{playlist_id}` - Delete playlist
- `POST /playlists/{playlist_id}/songs/{song_id}` - Add song to playlist
- `DELETE /playlists/{playlist_id}/songs/{song_id}` - Remove song from playlist

### Genres
- `POST /genres/` - Create new genre
- `GET /genres/` - List all genres
- `GET /genres/{genre_id}` - Get genre details
- `PUT /genres/{genre_id}` - Update genre
- `DELETE /genres/{genre_id}` - Delete genre

## Data Models

### User
- Basic user information (email, username, password)
- Artist status
- Profile information (bio, image)
- Relationships with songs, albums, and playlists

### Song
- Basic song information (title, duration, file path)
- Creator relationship
- Album relationship
- Genre relationships
- Like relationships

### Album
- Basic album information (title, release date, cover image)
- Creator relationship
- Song relationships

### Playlist
- Basic playlist information (name, description)
- Owner relationship
- Song relationships

### Genre
- Basic genre information (name, description)
- Song relationships

## Setup and Installation

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost/dbname"
export SECRET_KEY="your-secret-key"
```

4. Run the application:
```bash
uvicorn main:app --reload
```

## Dependencies

- FastAPI - Web framework
- SQLAlchemy - ORM
- Pydantic - Data validation
- PostgreSQL - Database
- Python-jose - JWT tokens
- Passlib - Password hashing
- Python-multipart - File uploads
- Alembic - Database migrations

## Security Features

- JWT-based authentication
- Password hashing
- Role-based access control
- File upload validation
- Input validation
- CORS middleware

## Future Improvements

- [ ] Add search functionality
- [ ] Implement file streaming
- [ ] Add user following system
- [ ] Implement comments and ratings
- [ ] Add social sharing features
- [ ] Implement caching
- [ ] Add analytics
- [ ] Implement recommendation system 