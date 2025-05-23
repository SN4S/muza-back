# Music Streaming Service API

A FastAPI-based music streaming service with PostgreSQL database.

## Features

- User authentication and authorization
- Song management
- Playlist creation and management
- Album and artist management
- Genre categorization
- Search functionality
- RESTful API endpoints

## Prerequisites

- Python 3.8+
- PostgreSQL
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd music-streaming-service
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```
DATABASE_URL=postgresql://username:password@localhost/music_streaming
SECRET_KEY=your-secret-key-here
```

5. Create the PostgreSQL database:
```bash
createdb music_streaming
```

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

2. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- POST `/auth/register` - Register a new user
- POST `/auth/token` - Login and get access token

### Songs
- GET `/songs` - List all songs
- POST `/songs` - Create a new song
- GET `/songs/{song_id}` - Get song details
- PUT `/songs/{song_id}` - Update song
- DELETE `/songs/{song_id}` - Delete song

### Playlists
- GET `/playlists` - List user's playlists
- POST `/playlists` - Create a new playlist
- GET `/playlists/{playlist_id}` - Get playlist details
- PUT `/playlists/{playlist_id}` - Update playlist
- DELETE `/playlists/{playlist_id}` - Delete playlist
- POST `/playlists/{playlist_id}/songs/{song_id}` - Add song to playlist
- DELETE `/playlists/{playlist_id}/songs/{song_id}` - Remove song from playlist

### Search
- GET `/search/songs` - Search songs
- GET `/search/artists` - Search artists
- GET `/search/albums` - Search albums
- GET `/search/playlists` - Search playlists
- GET `/search/genres` - Search genres

## Development

The project structure is organized as follows:

```
music-streaming-service/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   └── routers/
│       ├── __init__.py
│       ├── auth.py
│       ├── songs.py
│       ├── playlists.py
│       └── search.py
├── main.py
├── requirements.txt
└── README.md
```

## Security

- All endpoints except registration and login require authentication
- Passwords are hashed using bcrypt
- JWT tokens are used for authentication
- CORS is configured for security

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 