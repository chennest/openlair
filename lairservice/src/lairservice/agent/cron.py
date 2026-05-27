from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import json


@dataclass(frozen=True)
class CronJob:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool


class CronScheduler:
    def __init__(self, workspace_path: Path | str) -> None:
        self._path = Path(workspace_path).resolve() / ".scheduled_tasks.json"
        self._session_jobs: dict[str, CronJob] = {}

    def schedule_cron(self, cron: str, prompt: str, recurring: bool = True, durable: bool = True) -> str:
        error = self.validate_cron(cron)
        if error is not None:
            return error
        job = CronJob(id=f"cron_{uuid4().hex[:12]}", cron=cron, prompt=prompt, recurring=recurring, durable=durable)
        if durable:
            jobs = self._load_durable()
            jobs[job.id] = job
            self._save_durable(jobs)
        else:
            self._session_jobs[job.id] = job
        return json.dumps(asdict(job), ensure_ascii=False)

    def list_crons(self) -> str:
        jobs = self._all_jobs()
        return json.dumps([asdict(job) for job in jobs.values()], ensure_ascii=False)

    def cancel_cron(self, job_id: str) -> str:
        jobs = self._load_durable()
        if job_id in jobs:
            del jobs[job_id]
            self._save_durable(jobs)
            return f"Cancelled {job_id}"
        if job_id in self._session_jobs:
            del self._session_jobs[job_id]
            return f"Cancelled {job_id}"
        return f"Error: unknown cron {job_id}"

    def due_prompts(self, at: datetime) -> list[str]:
        due: list[str] = []
        durable_jobs = self._load_durable()
        for jobs in (durable_jobs, self._session_jobs):
            for job_id, job in list(jobs.items()):
                if cron_matches(job.cron, at):
                    due.append(job.prompt)
                    if not job.recurring:
                        del jobs[job_id]
        self._save_durable(durable_jobs)
        return due

    def validate_cron(self, cron: str) -> str | None:
        fields = cron.split()
        if len(fields) != 5:
            return "Error: cron must have 5 fields"
        ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
        for field, bounds in zip(fields, ranges, strict=True):
            for part in field.split(","):
                values = part[2:] if part.startswith("*/") else part
                if part.startswith("*/") and (not values.isdigit() or int(values) <= 0):
                    return f"Error: invalid cron field {field}"
                if "-" in values:
                    start, end = values.split("-", 1)
                    if not start.isdigit() or not end.isdigit() or not bounds[0] <= int(start) <= int(end) <= bounds[1]:
                        return f"Error: invalid cron field {field}"
                elif values != "*" and (not values.isdigit() or not bounds[0] <= int(values) <= bounds[1]):
                    return f"Error: invalid cron field {field}"
        return None

    def _all_jobs(self) -> dict[str, CronJob]:
        jobs = self._load_durable()
        jobs.update(self._session_jobs)
        return jobs

    def _load_durable(self) -> dict[str, CronJob]:
        if not self._path.exists():
            return {}
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return {job_id: CronJob(**job) for job_id, job in data.items()}

    def _save_durable(self, jobs: dict[str, CronJob]) -> None:
        self._path.write_text(
            json.dumps({job_id: asdict(job) for job_id, job in jobs.items()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    minute, hour, day, month, weekday = cron_expr.split()
    day_matches = _field_matches(day, dt.day)
    weekday_matches = _field_matches(weekday, dt.weekday())
    if day == "*" and weekday == "*":
        date_matches = True
    elif day == "*":
        date_matches = weekday_matches
    elif weekday == "*":
        date_matches = day_matches
    else:
        date_matches = day_matches or weekday_matches
    return (
        _field_matches(minute, dt.minute)
        and _field_matches(hour, dt.hour)
        and _field_matches(month, dt.month)
        and date_matches
    )


def _field_matches(field: str, value: int) -> bool:
    if field == "*":
        return True
    for part in field.split(","):
        if part.startswith("*/") and part[2:].isdigit() and int(part[2:]) > 0 and value % int(part[2:]) == 0:
            return True
        if "-" in part:
            start, end = part.split("-", 1)
            if start.isdigit() and end.isdigit() and int(start) <= value <= int(end):
                return True
        if part.isdigit() and int(part) == value:
            return True
    return False
