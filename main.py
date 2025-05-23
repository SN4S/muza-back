from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, songs, playlists, search

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Music Streaming Service",
    description="A FastAPI-based music streaming service",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(songs.router)
app.include_router(playlists.router)
app.include_router(search.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Music Streaming Service API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }
