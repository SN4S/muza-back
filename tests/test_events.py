from datetime import datetime, timedelta, timezone

import pytest

from app import models


def _event(song_id, **overrides):
    event = {
        "song_id": song_id,
        "started_at": "2026-11-01T12:00:00Z",
        "played_ms": 95_000,
        "end_reason": "completed",
        "source": "playlist",
        "source_id": 1,
    }
    event.update(overrides)
    return event


@pytest.mark.unit
class TestListeningEvents:

    def test_requires_auth(self, client, test_song):
        response = client.post("/events/listening", json={"events": [_event(test_song.id)]})
        assert response.status_code == 401

    def test_record_batch(self, client, db_session, auth_headers, test_user, test_song):
        response = client.post(
            "/events/listening",
            json={"events": [
                _event(test_song.id),
                _event(test_song.id, played_ms=4_000, end_reason="skipped", source=None, source_id=None),
            ]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == {"accepted": 2, "rejected_song_ids": []}

        events = db_session.query(models.ListeningEvent).order_by(models.ListeningEvent.id).all()
        assert [e.end_reason for e in events] == ["completed", "skipped"]
        assert all(e.user_id == test_user.id for e in events)
        assert events[1].played_ms == 4_000
        assert events[1].source is None

    def test_unknown_songs_are_dropped_and_reported(self, client, db_session, auth_headers, test_song):
        response = client.post(
            "/events/listening",
            json={"events": [_event(test_song.id), _event(99999)]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == {"accepted": 1, "rejected_song_ids": [99999]}
        assert db_session.query(models.ListeningEvent).count() == 1

    def test_future_timestamp_is_clamped(self, client, db_session, auth_headers, test_song):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        response = client.post(
            "/events/listening",
            json={"events": [_event(test_song.id, started_at=future)]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        stored = db_session.query(models.ListeningEvent).one().started_at
        if stored.tzinfo is None:  # SQLite drops tzinfo
            stored = stored.replace(tzinfo=timezone.utc)
        assert stored <= datetime.now(timezone.utc)

    @pytest.mark.parametrize("bad", [
        {"end_reason": "liked"},
        {"played_ms": -1},
        {"source": "x" * 33},
    ])
    def test_validation(self, client, auth_headers, test_song, bad):
        response = client.post(
            "/events/listening",
            json={"events": [_event(test_song.id, **bad)]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_empty_batch_rejected(self, client, auth_headers):
        response = client.post("/events/listening", json={"events": []}, headers=auth_headers)
        assert response.status_code == 422

    def test_history_is_per_user_newest_first(
            self, client, db_session, auth_headers, test_user, test_artist, test_song):
        base = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        for i, user in enumerate([test_user, test_user, test_artist]):
            db_session.add(models.ListeningEvent(
                user_id=user.id, song_id=test_song.id,
                started_at=base + timedelta(minutes=i),
                played_ms=1000 * (i + 1), end_reason="completed",
            ))
        db_session.commit()

        response = client.get("/events/listening/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert [e["played_ms"] for e in data] == [2000, 1000]
        assert all(e["user_id"] == test_user.id for e in data)
