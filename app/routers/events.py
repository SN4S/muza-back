"""Listening events: implicit-feedback collection for the recommendation system.

The client sends one event per playback session of a song (batched, so that
events recorded offline can be delivered later).
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/events",
    tags=["events"]
)


@router.post("/listening", response_model=schemas.ListeningEventBatchResult)
def record_listening_events(
        batch: schemas.ListeningEventBatch,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Store a batch of listening events for the current user.

    Events that reference songs which no longer exist are dropped (the song
    could have been deleted while the client was offline) and reported back,
    so the client can safely discard them instead of retrying forever.
    """
    requested_ids = {e.song_id for e in batch.events}
    existing_ids = {
        song_id for (song_id,) in
        db.query(models.Song.id).filter(models.Song.id.in_(requested_ids)).all()
    }

    now = datetime.now(timezone.utc)
    accepted = 0
    for event in batch.events:
        if event.song_id not in existing_ids:
            continue
        started_at = event.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        # Clamp client clocks that run ahead of the server
        if started_at > now:
            started_at = now
        db.add(models.ListeningEvent(
            user_id=current_user.id,
            song_id=event.song_id,
            started_at=started_at,
            played_ms=event.played_ms,
            end_reason=event.end_reason.value,
            source=event.source,
            source_id=event.source_id,
        ))
        accepted += 1

    db.commit()
    return schemas.ListeningEventBatchResult(
        accepted=accepted,
        rejected_song_ids=sorted(requested_ids - existing_ids),
    )


@router.get("/listening/me", response_model=List[schemas.ListeningEvent])
def get_my_listening_events(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(auth.get_current_active_user)
):
    """Listening history of the current user, newest first."""
    limit = max(1, min(limit, 500))
    return (
        db.query(models.ListeningEvent)
        .filter(models.ListeningEvent.user_id == current_user.id)
        .order_by(models.ListeningEvent.started_at.desc(), models.ListeningEvent.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
