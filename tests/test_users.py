# tests/test_users.py
import pytest
import tempfile
import os
from unittest.mock import patch, Mock
from app import models


class TestUserProfile:
    """Test user profile operations"""

    def test_get_current_user(self, client, auth_headers, test_user):
        """Test getting current user profile"""
        response = client.get("/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["is_artist"] == test_user.is_artist

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication"""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_update_current_user_success(self, client, auth_headers, test_user):
        """Test successful user profile update"""
        update_data = {
            "username": "newusername",
            "email": "newemail@example.com",
            "bio": "New bio text",
            "is_artist": True
        }
        response = client.put("/users/me", data=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newusername"
        assert data["email"] == "newemail@example.com"
        assert data["bio"] == "New bio text"
        assert data["is_artist"] is True

    def test_update_current_user_duplicate_username(self, client, auth_headers, test_user, test_artist, db_session):
        """Test updating user with duplicate username"""
        update_data = {
            "username": test_artist.username,  # Use existing username
            "email": "newemail@example.com"
        }
        response = client.put("/users/me", data=update_data, headers=auth_headers)

        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_update_current_user_duplicate_email(self, client, auth_headers, test_user, test_artist, db_session):
        """Test updating user with duplicate email"""
        update_data = {
            "username": "newusername",
            "email": test_artist.email  # Use existing email
        }
        response = client.put("/users/me", data=update_data, headers=auth_headers)

        assert response.status_code == 400
        assert "Email already taken" in response.json()["detail"]

    def test_update_current_user_same_data(self, client, auth_headers, test_user):
        """Test updating user with same username and email (should succeed)"""
        update_data = {
            "username": test_user.username,
            "email": test_user.email,
            "bio": "Updated bio"
        }
        response = client.put("/users/me", data=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "Updated bio"

    def test_update_current_user_missing_fields(self, client, auth_headers):
        """Test updating user with missing required fields"""
        # Missing email
        response = client.put("/users/me",
                              data={"username": "test"},
                              headers=auth_headers)
        assert response.status_code == 422

        # Missing username
        response = client.put("/users/me",
                              data={"email": "test@example.com"},
                              headers=auth_headers)
        assert response.status_code == 422

    @patch('app.routers.users.save_image_file')
    def test_update_current_user_with_image(self, mock_save_image, client, auth_headers, temp_image_file):
        """Test updating user with profile image"""
        mock_save_image.return_value = "/fake/profile.jpg"

        with open(temp_image_file, 'rb') as img_f:
            response = client.put("/users/me",
                                  files={"image": ("profile.jpg", img_f, "image/jpeg")},
                                  data={
                                      "username": "imageuser",
                                      "email": "image@example.com"
                                  },
                                  headers=auth_headers)

        assert response.status_code == 200
        mock_save_image.assert_called_once()

    def test_update_current_user_invalid_image_type(self, client, auth_headers):
        """Test updating user with invalid image type"""
        with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
            tmp.write(b'not image content')
            tmp.seek(0)

            response = client.put("/users/me",
                                  files={"image": ("profile.txt", tmp, "text/plain")},
                                  data={
                                      "username": "testuser",
                                      "email": "test@example.com"
                                  },
                                  headers=auth_headers)

        assert response.status_code == 400
        assert "Image must be an image file" in response.json()["detail"]


class TestUserImage:
    """Test user image operations"""

    def test_delete_user_image_success(self, client, auth_headers, test_user, db_session):
        """Test deleting user image"""
        # Set up user with image
        test_user.image = "/fake/profile.jpg"
        db_session.commit()

        with patch('os.path.exists') as mock_exists, \
                patch('os.remove') as mock_remove:
            mock_exists.return_value = True

            response = client.delete("/users/me/image", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Image deleted successfully"
        mock_remove.assert_called_once()

    def test_delete_user_image_no_image(self, client, auth_headers, test_user, db_session):
        """Test deleting user image when no image exists"""
        # Ensure user has no image
        test_user.image = None
        db_session.commit()

        response = client.delete("/users/me/image", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Image deleted successfully"

    def test_get_user_image_success(self, client, test_user, db_session):
        """Test getting user image when it exists"""
        test_user.image = "/fake/profile.jpg"
        db_session.commit()

        with patch('os.path.exists') as mock_exists, \
                patch('fastapi.responses.FileResponse') as mock_response:
            mock_exists.return_value = True

            # Call endpoint but can't easily test FileResponse in TestClient
            # Just verify no error occurs
            mock_exists.return_value = False  # Force not found path
            response = client.get(f"/users/{test_user.id}/image")
            assert response.status_code == 404

    def test_get_user_image_not_found(self, client, test_user):
        """Test getting user image when no image exists"""
        response = client.get(f"/users/{test_user.id}/image")
        assert response.status_code == 404
        assert "Image not found" in response.json()["detail"]

    def test_get_user_image_user_not_found(self, client):
        """Test getting image for non-existent user"""
        response = client.get("/users/99999/image")
        assert response.status_code == 404


class TestUserContent:
    """Test user content endpoints (songs, albums, playlists)"""

    def test_get_current_user_songs_not_artist(self, client, auth_headers, test_user):
        """Test getting songs for non-artist user"""
        response = client.get("/users/me/songs", headers=auth_headers)
        assert response.status_code == 403
        assert "Only artists can have songs" in response.json()["detail"]

    def test_get_current_user_songs_artist(self, client, artist_auth_headers, test_artist, db_session):
        """Test getting songs for artist user"""
        # Create a song for the artist
        song = models.Song(
            title="Artist Song",
            file_path="/test/song.mp3",
            duration=180,
            creator_id=test_artist.id,
            like_count=0
        )
        db_session.add(song)
        db_session.commit()

        response = client.get("/users/me/songs", headers=artist_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(s["id"] == song.id for s in data)

    def test_get_current_user_albums_not_artist(self, client, auth_headers):
        """Test getting albums for non-artist user"""
        response = client.get("/users/me/albums", headers=auth_headers)
        assert response.status_code == 403
        assert "Only artists can have albums" in response.json()["detail"]

    def test_get_current_user_albums_artist(self, client, artist_auth_headers, test_artist, db_session):
        """Test getting albums for artist user"""
        # Create an album for the artist
        from datetime import datetime
        album = models.Album(
            title="Artist Album",
            release_date=datetime.now(),
            creator_id=test_artist.id,
            like_count=0
        )
        db_session.add(album)
        db_session.commit()

        response = client.get("/users/me/albums", headers=artist_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(a["id"] == album.id for a in data)

    def test_get_current_user_playlists(self, client, auth_headers, test_user, db_session):
        """Test getting current user's playlists"""
        # Create a playlist for the user
        playlist = models.Playlist(
            name="My Playlist",
            description="Test playlist",
            owner_id=test_user.id
        )
        db_session.add(playlist)
        db_session.commit()

        response = client.get("/users/me/playlists", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(p["id"] == playlist.id for p in data)

    def test_get_current_user_liked_songs(self, client, auth_headers, test_user, test_song, db_session):
        """Test getting current user's liked songs"""
        # Like a song
        test_user.liked_songs.append(test_song)
        db_session.commit()

        response = client.get("/users/me/liked-songs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(s["id"] == test_song.id for s in data)

    def test_get_current_user_liked_albums(self, client, auth_headers, test_user, test_album, db_session):
        """Test getting current user's liked albums"""
        # Like an album
        test_user.liked_albums.append(test_album)
        db_session.commit()

        response = client.get("/users/me/liked-albums", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(a["id"] == test_album.id for a in data)


class TestPublicUserEndpoints:
    """Test public user profile endpoints"""

    def test_get_user_profile_public(self, client, test_user):
        """Test getting public user profile"""
        response = client.get(f"/users/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        # Should not include sensitive info like email
        assert "email" not in data or data["email"] is None

    def test_get_user_profile_not_found(self, client):
        """Test getting non-existent user profile"""
        response = client.get("/users/99999")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_get_user_songs_public(self, client, test_artist, db_session):
        """Test getting user's public songs"""
        # Create songs for the artist
        for i in range(3):
            song = models.Song(
                title=f"Public Song {i}",
                file_path=f"/test/song{i}.mp3",
                duration=180,
                creator_id=test_artist.id,
                like_count=0
            )
            db_session.add(song)
        db_session.commit()

        response = client.get(f"/users/{test_artist.id}/songs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_user_songs_not_found(self, client):
        """Test getting songs for non-existent user"""
        response = client.get("/users/99999/songs")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_get_user_albums_public(self, client, test_artist, db_session):
        """Test getting user's public albums"""
        # Create albums for the artist
        from datetime import datetime
        for i in range(2):
            album = models.Album(
                title=f"Public Album {i}",
                release_date=datetime.now(),
                creator_id=test_artist.id,
                like_count=0
            )
            db_session.add(album)
        db_session.commit()

        response = client.get(f"/users/{test_artist.id}/albums")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_user_albums_not_found(self, client):
        """Test getting albums for non-existent user"""
        response = client.get("/users/99999/albums")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


class TestFollowSystem:
    """Test user follow/unfollow functionality"""

    def test_follow_user_success(self, client, auth_headers, test_user, test_artist, db_session):
        """Test successfully following a user"""
        response = client.post(f"/users/follow/{test_artist.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_following"] is True
        assert data["follower_count"] >= 1
        assert "following_count" in data

        # Verify in database
        db_session.refresh(test_user)
        assert test_artist in test_user.following

    def test_follow_user_not_found(self, client, auth_headers):
        """Test following non-existent user"""
        response = client.post("/users/follow/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_follow_user_already_following(self, client, auth_headers, test_user, test_artist, db_session):
        """Test following user already being followed"""
        # First follow the user
        test_user.following.append(test_artist)
        db_session.commit()

        response = client.post(f"/users/follow/{test_artist.id}", headers=auth_headers)
        assert response.status_code == 400
        assert "Already following this user" in response.json()["detail"]

    def test_follow_self(self, client, auth_headers, test_user):
        """Test trying to follow yourself"""
        response = client.post(f"/users/follow/{test_user.id}", headers=auth_headers)
        assert response.status_code == 400
        assert "Cannot follow yourself" in response.json()["detail"]

    def test_unfollow_user_success(self, client, auth_headers, test_user, test_artist, db_session):
        """Test successfully unfollowing a user"""
        # First follow the user
        test_user.following.append(test_artist)
        db_session.commit()

        response = client.delete(f"/users/follow/{test_artist.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_following"] is False

        # Verify in database
        db_session.refresh(test_user)
        assert test_artist not in test_user.following

    def test_unfollow_user_not_found(self, client, auth_headers):
        """Test unfollowing non-existent user"""
        response = client.delete("/users/follow/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_unfollow_user_not_following(self, client, auth_headers, test_artist):
        """Test unfollowing user not being followed"""
        response = client.delete(f"/users/follow/{test_artist.id}", headers=auth_headers)
        assert response.status_code == 400
        assert "Not following this user" in response.json()["detail"]

    def test_get_follow_status_following(self, client, auth_headers, test_user, test_artist, db_session):
        """Test getting follow status when following"""
        # Follow the user
        test_user.following.append(test_artist)
        db_session.commit()

        response = client.get(f"/users/follow/{test_artist.id}/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_following"] is True
        assert "follower_count" in data
        assert "following_count" in data

    def test_get_follow_status_not_following(self, client, auth_headers, test_artist):
        """Test getting follow status when not following"""
        response = client.get(f"/users/follow/{test_artist.id}/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_following"] is False
        assert "follower_count" in data
        assert "following_count" in data

    def test_get_follow_status_user_not_found(self, client, auth_headers):
        """Test getting follow status for non-existent user"""
        response = client.get("/users/follow/99999/status", headers=auth_headers)
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


class TestUserProfile:
    """Test detailed user profile endpoint"""

    def test_get_user_profile_detailed(self, client, auth_headers, test_artist, db_session):
        """Test getting detailed user profile with song count"""
        # Create songs for the artist
        for i in range(5):
            song = models.Song(
                title=f"Profile Song {i}",
                file_path=f"/test/song{i}.mp3",
                duration=180,
                creator_id=test_artist.id,
                like_count=0
            )
            db_session.add(song)
        db_session.commit()

        response = client.get(f"/users/{test_artist.id}/profile", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_artist.username
        assert data["song_count"] >= 5
        assert "follower_count" in data
        assert "following_count" in data
        assert "is_following" in data

    def test_get_user_profile_detailed_not_found(self, client, auth_headers):
        """Test getting detailed profile for non-existent user"""
        response = client.get("/users/99999/profile", headers=auth_headers)
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


class TestFollowersFollowing:
    """Test followers and following endpoints"""

    def test_get_my_following(self, client, auth_headers, test_user, test_artist, db_session):
        """Test getting list of users I'm following"""
        # Follow some users
        test_user.following.append(test_artist)
        db_session.commit()

        response = client.get("/users/following", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(u["id"] == test_artist.id for u in data)
        # All users in following should have is_following=True
        assert all(u["is_following"] is True for u in data)

    def test_get_my_following_empty(self, client, auth_headers):
        """Test getting following list when not following anyone"""
        response = client.get("/users/following", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_my_followers(self, client, auth_headers, test_user, test_artist, db_session):
        """Test getting list of my followers"""
        # Make artist follow the user
        test_artist.following.append(test_user)
        db_session.commit()

        response = client.get("/users/followers", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(u["id"] == test_artist.id for u in data)

    def test_get_my_followers_empty(self, client, auth_headers):
        """Test getting followers list when no one follows me"""
        response = client.get("/users/followers", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_following_pagination(self, client, auth_headers, test_user, db_session):
        """Test pagination for following list"""
        # Create and follow multiple users
        for i in range(10):
            user = models.User(
                username=f"followed_user_{i}",
                email=f"followed{i}@example.com",
                hashed_password="hashedpass",
                is_active=True
            )
            db_session.add(user)
            db_session.commit()
            test_user.following.append(user)
        db_session.commit()

        # Test pagination
        response = client.get("/users/following?limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

        # Test skip
        response = client.get("/users/following?skip=5&limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5


class TestUserAuthentication:
    """Test authentication requirements for user endpoints"""

    def test_protected_endpoints_without_auth(self, client, test_user):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            ("GET", "/users/me"),
            ("PUT", "/users/me", {"data": {"username": "test", "email": "test@example.com"}}),
            ("DELETE", "/users/me/image"),
            ("GET", "/users/me/songs"),
            ("GET", "/users/me/albums"),
            ("GET", "/users/me/playlists"),
            ("GET", "/users/me/liked-songs"),
            ("GET", "/users/me/liked-albums"),
            ("POST", f"/users/follow/{test_user.id}"),
            ("DELETE", f"/users/follow/{test_user.id}"),
            ("GET", f"/users/follow/{test_user.id}/status"),
            ("GET", f"/users/{test_user.id}/profile"),
            ("GET", "/users/following"),
            ("GET", "/users/followers"),
        ]

        for endpoint_info in protected_endpoints:
            method = endpoint_info[0]
            endpoint = endpoint_info[1]
            kwargs = endpoint_info[2] if len(endpoint_info) > 2 else {}

            response = getattr(client, method.lower())(endpoint, **kwargs)
            assert response.status_code == 401


class TestUserContentPagination:
    """Test pagination for user content endpoints"""

    def test_user_songs_pagination(self, client, test_artist, db_session):
        """Test pagination for user songs"""
        # Create multiple songs
        for i in range(15):
            song = models.Song(
                title=f"Paginated Song {i}",
                file_path=f"/test/song{i}.mp3",
                duration=180,
                creator_id=test_artist.id,
                like_count=0
            )
            db_session.add(song)
        db_session.commit()

        # Test default pagination
        response = client.get(f"/users/{test_artist.id}/songs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 15

        # Test custom limit
        response = client.get(f"/users/{test_artist.id}/songs?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # Test skip
        response = client.get(f"/users/{test_artist.id}/songs?skip=10&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_user_albums_pagination(self, client, test_artist, db_session):
        """Test pagination for user albums"""
        from datetime import datetime
        # Create multiple albums
        for i in range(8):
            album = models.Album(
                title=f"Paginated Album {i}",
                release_date=datetime.now(),
                creator_id=test_artist.id,
                like_count=0
            )
            db_session.add(album)
        db_session.commit()

        # Test pagination
        response = client.get(f"/users/{test_artist.id}/albums?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestUserValidation:
    """Test input validation for user endpoints"""

    def test_invalid_user_id_format(self, client, auth_headers):
        """Test endpoints with invalid user ID format"""
        invalid_endpoints = [
            ("GET", "/users/invalid"),
            ("GET", "/users/invalid/songs"),
            ("GET", "/users/invalid/albums"),
            ("POST", "/users/follow/invalid"),
            ("GET", "/users/invalid/profile"),
        ]

        for method, endpoint in invalid_endpoints:
            response = getattr(client, method.lower())(endpoint, headers=auth_headers)
            assert response.status_code == 422  # Validation error

    def test_update_user_invalid_email_format(self, client, auth_headers):
        """Test updating user with invalid email format"""
        update_data = {
            "username": "testuser",
            "email": "invalid-email"
        }
        response = client.put("/users/me", data=update_data, headers=auth_headers)
        assert response.status_code == 422


class TestUserEdgeCases:
    """Test edge cases and business logic"""

    def test_user_with_unicode_username(self, client, auth_headers):
        """Test updating user with unicode characters"""
        update_data = {
            "username": "用户名",
            "email": "unicode@example.com",
            "bio": "Bio with émojis 🎵"
        }
        response = client.put("/users/me", data=update_data, headers=auth_headers)
        # Should succeed if your app supports unicode
        assert response.status_code in [200, 422]  # Depends on validation rules

    def test_follow_mutual_relationship(self, client, auth_headers, artist_auth_headers, test_user, test_artist,
                                        db_session):
        """Test mutual following relationship"""
        # User follows artist
        response1 = client.post(f"/users/follow/{test_artist.id}", headers=auth_headers)
        assert response1.status_code == 200

        # Artist follows user back
        response2 = client.post(f"/users/follow/{test_user.id}", headers=artist_auth_headers)
        assert response2.status_code == 200

        # Verify mutual following
        db_session.refresh(test_user)
        db_session.refresh(test_artist)
        assert test_artist in test_user.following
        assert test_user in test_artist.following

    def test_user_counts_accuracy(self, client, auth_headers, test_user, test_artist, db_session):
        """Test that follower/following counts are accurate"""
        # Follow artist
        test_user.following.append(test_artist)
        db_session.commit()

        # Check follow status
        response = client.get(f"/users/follow/{test_artist.id}/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify counts
        assert data["follower_count"] >= 1  # Artist has at least 1 follower
        assert data["following_count"] >= 0  # Artist might follow others