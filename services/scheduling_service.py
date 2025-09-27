
import asyncio
import os
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser, tz
from sqlalchemy import or_
from sqlalchemy.orm import Session

from instagram_agent import InstagramAgent
from models.database import ScheduledPost, SessionLocal, Topic
from services.image_upload_service import ImageUploadService


class SchedulingError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.details = details


class SchedulingService:
    """Manage creation and execution of scheduled Instagram posts."""

    DEFAULT_TIMEZONE = "UTC"
    MAX_ATTEMPTS = 3
    BACKOFF_SECONDS = (60, 300, 900)

    def __init__(self, images_dir: Optional[str] = None) -> None:
        self.images_dir = images_dir or os.path.abspath("generated_images")

    @staticmethod
    def parse_scheduled_datetime(
        scheduled_time: str,
        timezone_name: Optional[str] = None,
    ) -> Tuple[datetime, str]:
        if not scheduled_time:
            raise ValueError("scheduled_time is required")

        try:
            parsed_dt = parser.isoparse(scheduled_time)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid scheduled_time format: {exc}") from exc

        tz_name = timezone_name or SchedulingService.DEFAULT_TIMEZONE

        if parsed_dt.tzinfo is None:
            tzinfo = tz.gettz(tz_name)
            if tzinfo is None:
                raise ValueError(f"Unknown timezone: {tz_name}")
            parsed_dt = parsed_dt.replace(tzinfo=tzinfo)
        elif timezone_name:
            tzinfo = tz.gettz(timezone_name)
            if tzinfo is None:
                raise ValueError(f"Unknown timezone: {timezone_name}")
            parsed_dt = parsed_dt.astimezone(tzinfo)
            tz_name = timezone_name
        else:
            tz_name = parsed_dt.tzname() or tz_name

        return parsed_dt.astimezone(timezone.utc), tz_name

    @staticmethod
    def ensure_future(schedule_time_utc: datetime, grace_seconds: int = 5) -> None:
        now = datetime.now(timezone.utc)
        if schedule_time_utc <= now + timedelta(seconds=grace_seconds):
            raise ValueError("scheduled_time must be at least 5 seconds in the future")

    def schedule_post(
        self,
        db: Session,
        *,
        user_id: int,
        caption: str,
        schedule_time: datetime,
        timezone_name: str,
        image_url: Optional[str] = None,
        image_filename: Optional[str] = None,
        topic_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledPost:
        self.ensure_future(schedule_time)

        if not caption:
            raise ValueError("caption is required")

        if not image_url and not image_filename:
            raise ValueError("Either image_url or image_filename is required")

        scheduled = ScheduledPost(
            user_id=user_id,
            topic_id=topic_id,
            image_url=image_url,
            image_filename=image_filename,
            job_metadata=metadata or {},
            caption=caption,
            schedule_time=schedule_time,
            timezone=timezone_name,
            status="pending",
            attempts=0,
            max_attempts=self.MAX_ATTEMPTS,
        )

        db.add(scheduled)

        if topic_id:
            topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
            if topic:
                topic.scheduled_date = schedule_time
                topic.status = "scheduled"

        db.commit()
        db.refresh(scheduled)
        return scheduled

    def _resolve_image_url(self, scheduled_post: ScheduledPost) -> Tuple[Optional[str], str]:
        """Return a tuple of (local_path, public_url)."""
        local_path: Optional[str] = None

        if scheduled_post.image_filename:
            local_path = os.path.join(self.images_dir, scheduled_post.image_filename)
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local image not found: {local_path}")

            public_base = os.getenv('PUBLIC_BASE_URL')
            if public_base:
                candidate = f"{public_base.rstrip('/')}/serve-image/{scheduled_post.image_filename}"
                try:
                    if ImageUploadService._is_public_image_url(candidate):
                        scheduled_post.image_url = candidate
                        return local_path, candidate
                except Exception as exc:
                    print(f"[scheduler] PUBLIC_BASE_URL check failed: {exc}")

            refreshed_url = ImageUploadService.get_public_url(local_path)
            if refreshed_url:
                scheduled_post.image_url = refreshed_url
                return local_path, refreshed_url

        if scheduled_post.image_url:
            return local_path, scheduled_post.image_url

        raise ValueError("Unable to determine public image URL for scheduled post")

    def _handle_failure(
        self,
        db: Session,
        scheduled_post: ScheduledPost,
        error: Exception,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        scheduled_post.last_error = str(error)
        scheduled_post.last_error_details = error_details

        if scheduled_post.attempts >= scheduled_post.max_attempts:
            scheduled_post.status = "failed"
            scheduled_post.next_attempt_after = None
        else:
            scheduled_post.status = "retry"
            index = min(scheduled_post.attempts - 1, len(self.BACKOFF_SECONDS) - 1)
            delay = self.BACKOFF_SECONDS[index]
            scheduled_post.next_attempt_after = datetime.now(timezone.utc) + timedelta(seconds=delay)

        db.commit()

    def _retry_with_alternate_host(
        self,
        db: Session,
        scheduled_post: ScheduledPost,
        agent: InstagramAgent,
        caption: str,
        local_path: Optional[str],
        first_failure: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Re-host the image when Meta rejects the provided media URL."""
        if not local_path or not os.path.exists(local_path):
            return None

        error_payload = first_failure.get("error_details") if isinstance(first_failure, dict) else first_failure
        message = str(error_payload)
        if isinstance(error_payload, dict):
            error = error_payload.get("error") or error_payload
            message = str(error.get("message")) if isinstance(error, dict) else str(error_payload)

        normalized = message.lower()
        retryable = any(token in normalized for token in [
            "media download has failed",
            "only photo or video",
            "doesn't meet our requirements",
        ])

        if not retryable:
            return None

        alt_url = ImageUploadService.upload_to_postimg(local_path)
        if not alt_url:
            print('[scheduler] Alternate hosting (postimg) failed')
            return None

        print(f'[scheduler] Retrying with alternate image host: {alt_url}')
        scheduled_post.image_url = alt_url
        db.commit()

        second_attempt = agent.post_to_instagram(alt_url, caption)
        if isinstance(second_attempt, dict) and second_attempt.get("success"):
            second_attempt.setdefault("public_image_url", alt_url)
            return second_attempt

        print(f'[scheduler] Alternate host attempt still failed: {second_attempt}')
        if isinstance(second_attempt, dict):
            second_attempt.setdefault("error_details", error_payload)
        return None

    def _process_single_post(self, db: Session, scheduled_post: ScheduledPost, agent: InstagramAgent) -> None:
        scheduled_post.status = "processing"
        scheduled_post.last_attempt_at = datetime.now(timezone.utc)
        scheduled_post.attempts += 1
        db.commit()
        db.refresh(scheduled_post)

        local_path, image_url = self._resolve_image_url(scheduled_post)
        result = agent.post_to_instagram(image_url, scheduled_post.caption)

        if not isinstance(result, dict):
            raise SchedulingError("Instagram post returned unexpected payload", {"raw": result})

        if not result.get("success"):
            fallback_result = self._retry_with_alternate_host(
                db,
                scheduled_post,
                agent,
                scheduled_post.caption,
                local_path,
                result,
            )
            if fallback_result:
                result = fallback_result
            else:
                raise SchedulingError("Instagram post failed", result)

        scheduled_post.status = "completed"
        scheduled_post.posted_at = datetime.now(timezone.utc)
        result.setdefault("public_image_url", scheduled_post.image_url)
        scheduled_post.result_payload = result
        scheduled_post.last_error = None
        scheduled_post.last_error_details = None
        scheduled_post.next_attempt_after = None
        scheduled_post.image_url = result.get("public_image_url", scheduled_post.image_url)
        db.commit()

    def run_due_posts(self, limit: int = 5) -> Dict[str, Any]:
        summary = {"processed": 0, "completed": 0, "failed": 0}

        with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            due_posts: List[ScheduledPost] = (
                db.query(ScheduledPost)
                .filter(ScheduledPost.status.in_(["pending", "retry"]))
                .filter(ScheduledPost.schedule_time <= now)
                .filter(or_(ScheduledPost.next_attempt_after == None, ScheduledPost.next_attempt_after <= now))
                .order_by(ScheduledPost.schedule_time, ScheduledPost.id)
                .limit(limit)
                .all()
            )

            if not due_posts:
                return summary

            agent = InstagramAgent()

            for scheduled_post in due_posts:
                summary["processed"] += 1
                try:
                    self._process_single_post(db, scheduled_post, agent)
                    summary["completed"] += 1
                except SchedulingError as exc:
                    summary["failed"] += 1
                    self._handle_failure(db, scheduled_post, exc, exc.details)
                except Exception as exc:
                    summary["failed"] += 1
                    self._handle_failure(db, scheduled_post, exc, None)

        return summary


class ScheduledPostRunner:
    """Background task that periodically executes due scheduled posts."""

    def __init__(self, poll_interval: Optional[int] = None) -> None:
        self.poll_interval = poll_interval or int(os.getenv("SCHEDULER_POLL_INTERVAL", "30"))
        self.startup_delay = int(os.getenv("SCHEDULER_STARTUP_DELAY", "5"))
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._service = SchedulingService()

    async def start(self) -> None:
        if self._task is not None:
            return

        async def _runner() -> None:
            await asyncio.sleep(self.startup_delay)
            while not self._stop_event.is_set():
                try:
                    summary = self._service.run_due_posts()
                    if summary["processed"]:
                        print(f"[scheduler] summary: {summary}")
                except Exception as exc:
                    print(f"[scheduler] error: {exc}")
                finally:
                    await asyncio.sleep(self.poll_interval)

        self._task = asyncio.create_task(_runner())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._stop_event = asyncio.Event()

    @property
    def service(self) -> SchedulingService:
        return self._service
