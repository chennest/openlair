"""/api/todo /api/calendar /api/notes /api/habits /api/overview 路由。"""

from fastapi import APIRouter, Depends, Request

from lairservice.api.v1.deps import get_current_user
from lairservice.api.v1.schemas import (
    CreateEventInput,
    CreateHabitInput,
    CreateNoteInput,
    CreateTodoInput,
    UpdateEventInput,
    UpdateHabitInput,
    UpdateNoteInput,
    UpdateTodoInput,
)
from lairservice.core.envelope import ok_response
from lairservice.models.user import User

todo_router = APIRouter(prefix="/todo", tags=["todo"])


@todo_router.get("")
async def list_todos(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.todo_service.list(user.id))


@todo_router.post("")
async def create_todo(
    request: Request, payload: CreateTodoInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.todo_service.create(
            user_id=user.id, text=payload.text, quadrant=payload.quadrant or "", due=payload.due or ""
        )
    )


@todo_router.put("/{todo_id}")
async def update_todo(
    request: Request,
    todo_id: int,
    payload: UpdateTodoInput,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.todo_service.update(
            user_id=user.id, todo_id=todo_id, patch=payload.model_dump(exclude_unset=True)
        )
    )


@todo_router.delete("/{todo_id}")
async def remove_todo(
    request: Request, todo_id: int, _user: User = Depends(get_current_user)
) -> dict:
    request.app.state.todo_service.remove(todo_id=todo_id)
    return ok_response({"ok": True})


calendar_router = APIRouter(prefix="/calendar", tags=["calendar"])


@calendar_router.get("")
async def list_events(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.event_service.list(user.id))


@calendar_router.post("")
async def create_event(
    request: Request, payload: CreateEventInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.event_service.create(
            user_id=user.id,
            title=payload.title,
            event_date=payload.date,
            time=payload.time or "",
            location=payload.location or "",
        )
    )


@calendar_router.put("/{event_id}")
async def update_event(
    request: Request,
    event_id: int,
    payload: UpdateEventInput,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.event_service.update(
            user_id=user.id, event_id=event_id, patch=payload.model_dump(exclude_unset=True)
        )
    )


@calendar_router.delete("/{event_id}")
async def remove_event(
    request: Request, event_id: int, _user: User = Depends(get_current_user)
) -> dict:
    request.app.state.event_service.remove(event_id=event_id)
    return ok_response({"ok": True})


notes_router = APIRouter(prefix="/notes", tags=["notes"])


@notes_router.get("")
async def list_notes(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.note_service.list(user.id))


@notes_router.post("")
async def create_note(
    request: Request, payload: CreateNoteInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.note_service.create(
            user_id=user.id, title=payload.title or "", summary=payload.summary or "", tags=payload.tags or []
        )
    )


@notes_router.put("/{note_id}")
async def update_note(
    request: Request,
    note_id: int,
    payload: UpdateNoteInput,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.note_service.update(
            user_id=user.id, note_id=note_id, patch=payload.model_dump(exclude_unset=True)
        )
    )


@notes_router.delete("/{note_id}")
async def remove_note(
    request: Request, note_id: int, _user: User = Depends(get_current_user)
) -> dict:
    request.app.state.note_service.remove(note_id=note_id)
    return ok_response({"ok": True})


habits_router = APIRouter(prefix="/habits", tags=["habits"])


@habits_router.get("")
async def list_habits(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.habit_service.list(user.id))


@habits_router.post("")
async def create_habit(
    request: Request, payload: CreateHabitInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(request.app.state.habit_service.create(user_id=user.id, name=payload.name))


@habits_router.put("/{habit_id}")
async def update_habit(
    request: Request,
    habit_id: int,
    payload: UpdateHabitInput,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.habit_service.update(
            user_id=user.id, habit_id=habit_id, patch=payload.model_dump(exclude_unset=True)
        )
    )


@habits_router.delete("/{habit_id}")
async def remove_habit(
    request: Request, habit_id: int, _user: User = Depends(get_current_user)
) -> dict:
    request.app.state.habit_service.remove(habit_id=habit_id)
    return ok_response({"ok": True})


overview_router = APIRouter(prefix="/overview", tags=["overview"])


@overview_router.get("")
async def overview(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.overview_service.get(user_id=user.id))
