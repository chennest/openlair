"""词汇打字练习路由（薄 HTTP 层）：/api/vocab/*。"""

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import (
    FinishSessionInput,
    ImportBooksInput,
    StartSessionInput,
    SubmitAnswerInput,
    UpdateVocabProgressInput,
)
from app.core.envelope import ok_response
from app.models.user import User

vocabulary_router = APIRouter(prefix="/vocab", tags=["vocab"])


@vocabulary_router.get("/books")
async def list_vocab_books(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.vocab_service.list_books(user.id))


@vocabulary_router.post("/books/import")
async def import_vocab_book(
    request: Request, payload: ImportBooksInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.vocab_service.import_book(
            user_id=user.id,
            name=payload.name,
            scope=payload.scope,
            lang=payload.lang,
            text=payload.text,
        )
    )


@vocabulary_router.delete("/books/{book_id}")
async def delete_vocab_book(
    request: Request, book_id: int, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(request.app.state.vocab_service.delete_book(user_id=user.id, book_id=book_id))


@vocabulary_router.get("/books/{book_id}/words")
async def list_book_words(
    request: Request,
    book_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.vocab_service.list_book_words(book_id, limit=limit, offset=offset, user_id=user.id)
    )


@vocabulary_router.post("/practice/sessions")
async def start_practice_session(
    request: Request, payload: StartSessionInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.vocab_service.start_session(
            user_id=user.id,
            book_id=payload.bookId,
            mode=payload.mode,
            new_limit=payload.newLimit,
            review_limit=payload.reviewLimit,
            source=payload.source,
        )
    )


@vocabulary_router.post("/practice/sessions/{session_id}/answers")
async def submit_practice_answer(
    request: Request, session_id: int, payload: SubmitAnswerInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.vocab_service.submit_answer(
            user_id=user.id,
            session_id=session_id,
            word_id=payload.wordId,
            correct=payload.correct,
            wrong_times=payload.wrongTimes,
            duration_ms=payload.durationMs,
        )
    )


@vocabulary_router.post("/practice/sessions/{session_id}/finish")
async def finish_practice_session(
    request: Request, session_id: int, payload: FinishSessionInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.vocab_service.finish_session(
            user_id=user.id, session_id=session_id, duration_sec=payload.durationSec
        )
    )


@vocabulary_router.get("/review/wrong")
async def list_wrong_words(
    request: Request,
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.vocab_service.list_wrong_words(user.id, limit=limit))


@vocabulary_router.get("/review/collect")
async def list_collected_words(
    request: Request,
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.vocab_service.list_collected_words(user.id, limit=limit))


@vocabulary_router.put("/progress/{word_id}")
async def update_vocab_progress(
    request: Request, word_id: int, payload: UpdateVocabProgressInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.vocab_service.update_progress(
            user_id=user.id, word_id=word_id, patch=payload.model_dump(exclude_unset=True)
        )
    )


@vocabulary_router.get("/stats")
async def vocab_stats(
    request: Request,
    tzOffset: int = Query(default=0, ge=-840, le=840),
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.vocab_service.stats(user.id, tz_offset=tzOffset))
