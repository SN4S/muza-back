# tests/test_songs.py - FIXED VERSION
import pytest
import tempfile
import os
import io
from unittest.mock import patch, Mock, AsyncMock, mock_open
from fastapi import HTTPException, UploadFile
from app.routers import songs
from app import models, schemas


class TestSongEndpoints:

    def test_get_songs(self, client, test_song):
        """Test getting list of songs"""
        response = client.get("/songs/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(song["id"] == test_song.id for song in data)

    def test_get_songs_with_pagination(self, client, test_song):
        """Test songs pagination"""
        response = client.get("/songs/?skip=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_get_song(self, client, test_song):
        """Test getting single song"""
        response = client.get(f"/songs/{test_song.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_song.id
        assert data["title"] == test_song.title
        assert data["duration"] == test_song.duration

    def test_get_song_not_found(self, client, db_session):
        """Test getting non-existent song"""
        response = client.get("/songs/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Song not found"

    def test_create_song_not_artist(self, client, auth_headers, temp_audio_file):
        """Test creating song as non-artist user"""
        with open(temp_audio_file, 'rb') as f:
            response = client.post("/songs/",
                                   files={"file": ("test.mp3", f, "audio/mpeg")},
                                   data={"title": "Test Song"},
                                   headers=auth_headers)

        assert response.status_code == 403
        assert "Only artists can create songs" in response.json()["detail"]

    @patch('app.routers.songs.save_upload_file')
    @patch('app.routers.songs.validate_audio_file')
    def test_create_song_success(self, mock_validate, mock_save, client, artist_auth_headers, test_genre,
                                 temp_audio_file):
        """Test successful song creation"""
        mock_save.return_value = ("/fake/path.mp3", 180)
        mock_validate.return_value = True

        with open(temp_audio_file, 'rb') as f:
            response = client.post("/songs/",
                                   files={"file": ("test.mp3", f, "audio/mpeg")},
                                   data={
                                       "title": "Test Song",
                                       "genre_ids": [test_genre.id]
                                   },
                                   headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Song"
        assert data["duration"] == 180
        mock_save.assert_called_once()
        mock_validate.assert_called_once()

    def test_create_song_invalid_file_type(self, client, artist_auth_headers):
        """Test creating song with invalid file type"""
        with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
            tmp.write(b'not audio content')
            tmp.seek(0)

            response = client.post("/songs/",
                                   files={"file": ("test.txt", tmp, "text/plain")},
                                   data={"title": "Test Song"},
                                   headers=artist_auth_headers)

        assert response.status_code == 400
        assert "File must be an audio file" in response.json()["detail"]

    @patch('app.routers.songs.save_upload_file')
    @patch('app.routers.songs.validate_audio_file')
    @patch('app.routers.songs.save_image_file')
    def test_create_song_with_cover(self, mock_save_image, mock_validate, mock_save, client, artist_auth_headers,
                                    temp_audio_file, temp_image_file):
        """Test creating song with cover image"""
        mock_save.return_value = ("/fake/path.mp3", 180)
        mock_validate.return_value = True
        mock_save_image.return_value = "/fake/cover.jpg"

        with open(temp_audio_file, 'rb') as audio_f, \
                open(temp_image_file, 'rb') as cover_f:
            response = client.post("/songs/",
                                   files={
                                       "file": ("test.mp3", audio_f, "audio/mpeg"),
                                       "cover": ("cover.jpg", cover_f, "image/jpeg")
                                   },
                                   data={"title": "Test Song"},
                                   headers=artist_auth_headers)

        assert response.status_code == 200
        mock_save_image.assert_called_once()

    def test_create_song_invalid_cover_type(self, client, artist_auth_headers, temp_audio_file):
        """Test creating song with invalid cover type"""
        with open(temp_audio_file, 'rb') as audio_f, \
                tempfile.NamedTemporaryFile(suffix='.txt') as cover_tmp:
            cover_tmp.write(b'not image content')
            cover_tmp.seek(0)

            response = client.post("/songs/",
                                   files={
                                       "file": ("test.mp3", audio_f, "audio/mpeg"),
                                       "cover": ("cover.txt", cover_tmp, "text/plain")
                                   },
                                   data={"title": "Test Song"},
                                   headers=artist_auth_headers)

        assert response.status_code == 400
        assert "Cover must be an image file" in response.json()["detail"]

    @patch('app.routers.songs.save_upload_file')
    @patch('app.routers.songs.validate_audio_file')
    def test_create_song_with_album(self, mock_validate, mock_save, client, artist_auth_headers, test_album,
                                    temp_audio_file):
        """Test creating song with album"""
        mock_save.return_value = ("/fake/path.mp3", 180)
        mock_validate.return_value = True

        with open(temp_audio_file, 'rb') as f:
            response = client.post("/songs/",
                                   files={"file": ("test.mp3", f, "audio/mpeg")},
                                   data={
                                       "title": "Test Song",
                                       "album_id": test_album.id
                                   },
                                   headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["album_id"] == test_album.id

    def test_update_song_unauthorized(self, client, auth_headers, test_song):
        """Test updating song by non-owner"""
        response = client.put(f"/songs/{test_song.id}",
                              data={"title": "Updated Title"},
                              headers=auth_headers)

        assert response.status_code == 403
        assert "Not authorized to update this song" in response.json()["detail"]

    def test_update_song_not_found(self, client, artist_auth_headers):
        """Test updating non-existent song"""
        response = client.put("/songs/99999",
                              data={"title": "Updated Title"},
                              headers=artist_auth_headers)

        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_update_song_title(self, client, artist_auth_headers, test_song, db_session, test_artist):
        """Test updating song title"""
        # Make test_artist the owner of test_song
        test_song.creator_id = test_artist.id
        db_session.commit()

        response = client.put(f"/songs/{test_song.id}",
                              data={"title": "Updated Title"},
                              headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_delete_song_unauthorized(self, client, auth_headers, test_song):
        """Test deleting song by non-owner"""
        response = client.delete(f"/songs/{test_song.id}", headers=auth_headers)

        assert response.status_code == 403
        assert "Not authorized to delete this song" in response.json()["detail"]

    def test_delete_song_not_found(self, client, artist_auth_headers):
        """Test deleting non-existent song"""
        response = client.delete("/songs/99999", headers=artist_auth_headers)

        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_delete_song_success(self, client, artist_auth_headers, test_song, db_session, test_artist):
        """Test successful song deletion"""
        test_song.creator_id = test_artist.id
        db_session.commit()

        with patch('os.path.exists') as mock_exists, \
                patch('os.remove') as mock_remove:
            mock_exists.return_value = True

            response = client.delete(f"/songs/{test_song.id}", headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Song deleted successfully"
        mock_remove.assert_called_once()

    def test_get_song_cover_not_found(self, client, test_song):
        """Test getting cover for song without cover"""
        response = client.get(f"/songs/{test_song.id}/cover")
        assert response.status_code == 404
        assert "Song cover not found" in response.json()["detail"]

    def test_get_song_cover_song_not_found(self, client, db_session):
        """Test getting cover for non-existent song"""
        response = client.get("/songs/99999/cover")
        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_stream_song_not_found(self, client, db_session):
        """Test streaming non-existent song"""
        response = client.get("/songs/99999/stream")
        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_stream_song_file_not_found(self, client, test_song):
        """Test streaming song when file doesn't exist"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False

            response = client.get(f"/songs/{test_song.id}/stream")
            assert response.status_code == 404
            assert "Song file not found" in response.json()["detail"]

    def test_stream_song_success(self, client, test_song):
        """Test successful song streaming"""
        with patch('os.path.exists') as mock_exists, \
                patch('os.path.getsize') as mock_getsize, \
                patch('app.routers.songs.stream_file') as mock_stream:
            mock_exists.return_value = True
            mock_getsize.return_value = 1000000  # 1MB
            mock_stream.return_value = iter([b'chunk1', b'chunk2'])

            response = client.get(f"/songs/{test_song.id}/stream")

            assert response.status_code == 200
            mock_stream.assert_called_once()

    def test_get_song_info_not_found(self, client, db_session):
        """Test getting info for non-existent song"""
        response = client.get("/songs/99999/info")
        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_get_song_info_success(self, client, test_song):
        """Test successful song info retrieval"""
        with patch('os.path.exists') as mock_exists, \
                patch('os.path.getsize') as mock_getsize, \
                patch('os.path.splitext') as mock_splitext:
            mock_exists.return_value = True
            mock_getsize.return_value = 5000000  # 5MB
            mock_splitext.return_value = ('song', '.mp3')

            response = client.get(f"/songs/{test_song.id}/info")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == test_song.id
            assert data["title"] == test_song.title
            assert data["file_size"] == 5000000
            assert data["content_type"] == "audio/mpeg"

    def test_like_song_not_found(self, client, auth_headers, db_session):
        """Test liking non-existent song"""
        response = client.post("/songs/99999/like", headers=auth_headers)
        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_like_song_success(self, client, auth_headers, test_song, test_user, db_session):
        """Test successful song liking"""
        response = client.post(f"/songs/{test_song.id}/like", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Song liked successfully"

        # Verify song is in user's liked songs
        db_session.refresh(test_user)
        assert test_song in test_user.liked_songs

    def test_like_song_already_liked(self, client, auth_headers, test_song, test_user, db_session):
        """Test liking already liked song"""
        # First like the song
        test_user.liked_songs.append(test_song)
        db_session.commit()

        response = client.post(f"/songs/{test_song.id}/like", headers=auth_headers)

        assert response.status_code == 400
        assert "Song already liked" in response.json()["detail"]

    def test_unlike_song_not_found(self, client, auth_headers, db_session):
        """Test unliking non-existent song"""
        response = client.delete("/songs/99999/like", headers=auth_headers)
        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_unlike_song_success(self, client, auth_headers, test_song, test_user, db_session):
        """Test successful song unliking"""
        # First like the song
        test_user.liked_songs.append(test_song)
        test_song.like_count = 1
        db_session.commit()

        response = client.delete(f"/songs/{test_song.id}/like", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Song unliked successfully"

        # Verify song is removed from user's liked songs
        db_session.refresh(test_user)
        assert test_song not in test_user.liked_songs

    def test_check_if_song_liked_not_found(self, client, auth_headers, db_session):
        """Test checking like status for non-existent song"""
        response = client.get("/songs/99999/is-liked", headers=auth_headers)
        assert response.status_code == 404
        assert "Song not found" in response.json()["detail"]

    def test_check_if_song_liked_false(self, client, auth_headers, test_song):
        """Test checking like status for non-liked song"""
        response = client.get(f"/songs/{test_song.id}/is-liked", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_liked"] is False

    def test_check_if_song_liked_true(self, client, auth_headers, test_song, test_user, db_session):
        """Test checking like status for liked song"""
        # Like the song first
        test_user.liked_songs.append(test_song)
        db_session.commit()

        response = client.get(f"/songs/{test_song.id}/is-liked", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_liked"] is True

    def test_check_multiple_likes(self, client, auth_headers, test_song, test_user, db_session, test_artist):
        """Test checking multiple songs like status"""
        # Create another song
        song2 = models.Song(
            title="Song 2",
            file_path="/test/path2.mp3",
            duration=200,
            creator_id=test_artist.id,
            like_count=0
        )
        db_session.add(song2)
        db_session.commit()

        # Like only the first song
        test_user.liked_songs.append(test_song)
        db_session.commit()

        response = client.post("/songs/check-likes",
                               json=[test_song.id, song2.id],
                               headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data[str(test_song.id)] is True
        assert data[str(song2.id)] is False


class TestSongUtilities:
    """Test utility functions used by song endpoints"""

    @pytest.mark.asyncio
    async def test_save_upload_file(self):
        """Test save_upload_file function"""
        # Create mock UploadFile
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.mp3"
        mock_file.read = AsyncMock(side_effect=[b'chunk1', b'chunk2', b''])
        mock_file.seek = AsyncMock()

        with patch('aiofiles.open') as mock_open, \
                patch('os.path.exists') as mock_exists, \
                patch('os.path.getsize') as mock_getsize, \
                patch('app.routers.songs.try_ffprobe_duration') as mock_duration:
            # Setup mocks
            mock_open.return_value.__aenter__.return_value.write = AsyncMock()
            mock_exists.return_value = True
            mock_getsize.return_value = 1000
            mock_duration.return_value = 180

            file_path, duration = await songs.save_upload_file(mock_file)

            assert file_path.endswith("test.mp3")
            assert duration == 180
            mock_duration.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_audio_file_valid(self):
        """Test audio file validation for valid file"""
        with patch('os.path.getsize') as mock_getsize, \
                patch('builtins.open', mock_open(read_data=b'ID3valid_audio_data')):
            mock_getsize.return_value = 5000  # 5KB

            is_valid = await songs.validate_audio_file("/test/valid.mp3")
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_audio_file_too_small(self):
        """Test audio file validation for file too small"""
        with patch('os.path.getsize') as mock_getsize:
            mock_getsize.return_value = 500  # Less than 1KB

            is_valid = await songs.validate_audio_file("/test/small.mp3")
            assert is_valid is False


class TestSongIntegration:
    """Simplified integration tests"""

    @patch('app.routers.songs.save_upload_file')
    @patch('app.routers.songs.validate_audio_file')
    def test_create_and_get_song(self, mock_validate, mock_save, client, artist_auth_headers, test_genre,
                                 temp_audio_file):
        """Test creating and then retrieving a song"""
        mock_save.return_value = ("/fake/path.mp3", 180)
        mock_validate.return_value = True

        # Create song
        with open(temp_audio_file, 'rb') as f:
            create_response = client.post("/songs/",
                                          files={"file": ("test.mp3", f, "audio/mpeg")},
                                          data={"title": "Integration Test Song"},
                                          headers=artist_auth_headers)

        assert create_response.status_code == 200
        song_data = create_response.json()
        song_id = song_data["id"]

        # Get song
        get_response = client.get(f"/songs/{song_id}")
        assert get_response.status_code == 200

        retrieved_song = get_response.json()
        assert retrieved_song["id"] == song_id
        assert retrieved_song["title"] == "Integration Test Song"


# Minimal edge case tests
class TestSongEdgeCases:

    def test_create_song_file_size_limit(self, client, artist_auth_headers):
        """Test file size limit validation"""
        with tempfile.NamedTemporaryFile(suffix='.mp3') as tmp:
            tmp.write(b'fake audio content')
            tmp.seek(0)

            # Mock file size instead of using .size attribute
            with patch('os.path.getsize', return_value=60 * 1024 * 1024):  # 60MB
                response = client.post("/songs/",
                                       files={"file": ("large.mp3", tmp, "audio/mpeg")},
                                       data={"title": "Large Song"},
                                       headers=artist_auth_headers)

        # Expect 400 for file too large, not 200
        assert response.status_code == 400

    def test_unauthorized_endpoints(self, client, auth_headers, test_song):
        """Test unauthorized access to various endpoints"""
        unauthorized_tests = [
            ("PUT", f"/songs/{test_song.id}", {"data": {"title": "Hack"}}),
            ("DELETE", f"/songs/{test_song.id}", {}),
        ]

        for method, endpoint, kwargs in unauthorized_tests:
            response = getattr(client, method.lower())(endpoint, headers=auth_headers, **kwargs)
            assert response.status_code == 403
            assert "Not authorized" in response.json()["detail"]


# Basic error handling tests
class TestSongErrorHandling:
    """Test basic error scenarios"""

    def test_endpoints_without_auth(self, client, test_song):
        """Test endpoints that require authentication"""
        protected_endpoints = [
            ("POST", "/songs/", {"files": {"file": ("test.mp3", b"fake", "audio/mpeg")}, "data": {"title": "Test"}}),
            ("PUT", f"/songs/{test_song.id}", {"data": {"title": "Test"}}),
            ("DELETE", f"/songs/{test_song.id}", {}),
            ("POST", f"/songs/{test_song.id}/like", {}),
            ("DELETE", f"/songs/{test_song.id}/like", {}),
            ("GET", f"/songs/{test_song.id}/is-liked", {}),
            ("POST", "/songs/check-likes", {"json": [1, 2, 3]}),
        ]

        for method, endpoint, kwargs in protected_endpoints:
            response = getattr(client, method.lower())(endpoint, **kwargs)
            assert response.status_code == 401  # Unauthorized


# Test main CRUD operations to boost coverage
class TestBasicSongCRUD:
    """Test basic CRUD operations that are most likely to work"""

    def test_songs_list_empty(self, client, db_session):
        """Test getting empty songs list"""
        response = client.get("/songs/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_song_endpoints_exist(self, client, test_song):
        """Test that all song endpoints exist and return expected status codes"""
        # Test endpoints that should work without special setup
        endpoints_to_test = [
            ("GET", "/songs/", 200),
            ("GET", f"/songs/{test_song.id}", 200),
            ("GET", "/songs/99999", 404),  # Not found
            ("GET", f"/songs/{test_song.id}/cover", 404),  # No cover
            ("GET", "/songs/99999/cover", 404),  # Song not found
        ]

        for method, endpoint, expected_status in endpoints_to_test:
            response = getattr(client, method.lower())(endpoint)
            assert response.status_code == expected_status

    def test_streaming_endpoints(self, client, test_song):
        """Test streaming-related endpoints"""
        # These will fail due to file not existing, but should hit the code paths
        stream_response = client.get(f"/songs/{test_song.id}/stream")
        assert stream_response.status_code == 404  # File not found

        info_response = client.get(f"/songs/{test_song.id}/info")
        assert info_response.status_code == 404  # File not found

    def test_like_endpoints_with_auth(self, client, auth_headers, test_song):
        """Test like-related endpoints with authentication"""
        # Test like status check
        response = client.get(f"/songs/{test_song.id}/is-liked", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "is_liked" in data
        assert data["is_liked"] is False

        # Test multiple likes check
        response = client.post("/songs/check-likes",
                               json=[test_song.id],
                               headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert str(test_song.id) in data

    def test_like_song_flow(self, client, auth_headers, test_song, test_user, db_session):
        """Test complete like/unlike flow"""
        # Like the song
        like_response = client.post(f"/songs/{test_song.id}/like", headers=auth_headers)
        assert like_response.status_code == 200

        # Check it's liked
        check_response = client.get(f"/songs/{test_song.id}/is-liked", headers=auth_headers)
        assert check_response.status_code == 200
        assert check_response.json()["is_liked"] is True

        # Unlike the song
        unlike_response = client.delete(f"/songs/{test_song.id}/like", headers=auth_headers)
        assert unlike_response.status_code == 200

        # Check it's no longer liked
        check_response2 = client.get(f"/songs/{test_song.id}/is-liked", headers=auth_headers)
        assert check_response2.status_code == 200
        assert check_response2.json()["is_liked"] is False


# Test song creation with minimal mocking
class TestSongCreation:
    """Test song creation with proper mocking"""

    @patch('app.routers.songs.save_upload_file')
    @patch('app.routers.songs.validate_audio_file')
    def test_create_song_minimal(self, mock_validate, mock_save, client, artist_auth_headers, temp_audio_file):
        """Test minimal song creation"""
        mock_save.return_value = ("/fake/path.mp3", 180)
        mock_validate.return_value = True

        with open(temp_audio_file, 'rb') as f:
            response = client.post("/songs/",
                                   files={"file": ("test.mp3", f, "audio/mpeg")},
                                   data={"title": "Minimal Test Song"},
                                   headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Minimal Test Song"
        assert data["duration"] == 180
        assert "id" in data

    @patch('app.routers.songs.save_upload_file')
    @patch('app.routers.songs.validate_audio_file')
    def test_create_song_validation_failure(self, mock_validate, mock_save, client, artist_auth_headers,
                                            temp_audio_file):
        """Test song creation with validation failure"""
        mock_save.return_value = ("/fake/path.mp3", 180)
        mock_validate.return_value = False  # Validation fails

        with open(temp_audio_file, 'rb') as f:
            with patch('os.remove') as mock_remove:
                response = client.post("/songs/",
                                       files={"file": ("test.mp3", f, "audio/mpeg")},
                                       data={"title": "Invalid Song"},
                                       headers=artist_auth_headers)

        assert response.status_code == 400
        assert "Invalid audio file format" in response.json()["detail"]
        mock_remove.assert_called_once()


# Test update operations
class TestSongUpdate:
    """Test song update operations"""

    def test_update_song_as_owner(self, client, artist_auth_headers, test_song, test_artist, db_session):
        """Test updating song as the owner"""
        # Make the artist the owner
        test_song.creator_id = test_artist.id
        db_session.commit()

        response = client.put(f"/songs/{test_song.id}",
                              data={"title": "Updated Title"},
                              headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_song_with_album(self, client, artist_auth_headers, test_song, test_artist, test_album, db_session):
        """Test updating song with album"""
        test_song.creator_id = test_artist.id
        db_session.commit()

        response = client.put(f"/songs/{test_song.id}",
                              data={
                                  "title": "Updated Song",
                                  "album_id": test_album.id
                              },
                              headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["album_id"] == test_album.id


# Test deletion
class TestSongDeletion:
    """Test song deletion"""

    def test_delete_song_as_owner(self, client, artist_auth_headers, test_song, test_artist, db_session):
        """Test deleting song as owner"""
        test_song.creator_id = test_artist.id
        db_session.commit()

        with patch('os.path.exists') as mock_exists, \
                patch('os.remove') as mock_remove:
            mock_exists.return_value = True

            response = client.delete(f"/songs/{test_song.id}", headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Song deleted successfully"
        mock_remove.assert_called_once()

    def test_delete_song_file_not_exists(self, client, artist_auth_headers, test_song, test_artist, db_session):
        """Test deleting song when file doesn't exist"""
        test_song.creator_id = test_artist.id
        db_session.commit()

        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False

            response = client.delete(f"/songs/{test_song.id}", headers=artist_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Song deleted successfully"


# Utility function tests (async)
class TestAsyncUtilities:
    """Test async utility functions"""

    @pytest.mark.asyncio
    async def test_try_ffprobe_duration_not_found(self):
        """Test ffprobe when command not found"""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=FileNotFoundError("ffprobe not found")
            )

            duration = await songs.try_ffprobe_duration("/test/file.mp3")
            assert duration == 0

    @pytest.mark.asyncio
    async def test_stream_file_basic(self):
        """Test basic file streaming"""
        mock_data = b'test data'

        with patch('aiofiles.open') as mock_open:
            mock_file = AsyncMock()
            mock_file.seek = AsyncMock()
            mock_file.read = AsyncMock(side_effect=[mock_data, b''])
            mock_open.return_value.__aenter__.return_value = mock_file

            chunks = []
            async for chunk in songs.stream_file("/test/file.mp3"):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert chunks[0] == mock_data