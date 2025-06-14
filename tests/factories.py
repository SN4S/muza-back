import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.models import User, Song, Album, Playlist, Genre
from app.auth import get_password_hash


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with session management."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"


class UserFactory(BaseFactory):
    """Factory for creating test users."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    hashed_password = factory.LazyFunction(lambda: get_password_hash("testpass123"))
    is_active = True
    is_artist = False
    bio = factory.Faker("text", max_nb_chars=200)


class ArtistFactory(UserFactory):
    """Factory for creating test artists."""

    is_artist = True


class GenreFactory(BaseFactory):
    """Factory for creating test genres."""

    class Meta:
        model = Genre

    name = factory.Iterator(["Rock", "Pop", "Hip Hop", "Jazz", "Classical", "Electronic"])


class SongFactory(BaseFactory):
    """Factory for creating test songs."""

    class Meta:
        model = Song

    title = factory.Faker("sentence", nb_words=3)
    duration = factory.Faker("random_int", min=60, max=300)
    file_path = factory.Faker("file_path", extension="mp3")
    creator_id = factory.SubFactory(UserFactory)


class AlbumFactory(BaseFactory):
    """Factory for creating test albums."""

    class Meta:
        model = Album

    title = factory.Faker("sentence", nb_words=2)
    release_date = factory.Faker("date_this_decade")
    creator_id = factory.SubFactory(ArtistFactory)


class PlaylistFactory(BaseFactory):
    """Factory for creating test playlists."""

    class Meta:
        model = Playlist

    name = factory.Faker("sentence", nb_words=2)
    description = factory.Faker("text", max_nb_chars=100)
    owner_id = factory.SubFactory(UserFactory)


# Utility functions for tests
def create_user_with_songs(session, song_count=3):
    """Create a user with multiple songs."""
    UserFactory._meta.sqlalchemy_session = session
    SongFactory._meta.sqlalchemy_session = session

    user = UserFactory()
    songs = SongFactory.create_batch(song_count, creator_id=user.id)

    return user, songs


def create_artist_with_album(session, song_count=5):
    """Create an artist with an album containing songs."""
    UserFactory._meta.sqlalchemy_session = session
    AlbumFactory._meta.sqlalchemy_session = session
    SongFactory._meta.sqlalchemy_session = session

    artist = ArtistFactory()
    album = AlbumFactory(creator_id=artist.id)
    songs = SongFactory.create_batch(song_count, creator_id=artist.id, album_id=album.id)

    return artist, album, songs


def create_playlist_with_songs(session, song_count=4):
    """Create a playlist with songs."""
    PlaylistFactory._meta.sqlalchemy_session = session
    SongFactory._meta.sqlalchemy_session = session

    playlist = PlaylistFactory()
    songs = SongFactory.create_batch(song_count)

    # Add songs to playlist (assuming many-to-many relationship)
    for song in songs:
        playlist.songs.append(song)

    session.commit()
    return playlist, songs