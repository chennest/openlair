from pathlib import Path
import os

from fastapi import FastAPI

from lairservice.api.routes import router
from lairservice.db.session import create_database_engine, create_session_factory, init_database
from lairservice.models.gateway import ModelGateway, create_model_gateway_from_config
from lairservice.modules.notes import NotesRepository, NotesService
from lairservice.runtime.langgraph_runtime import LangGraphAssistantRuntime


def create_app(
    database_url: str = "sqlite+pysqlite:///./data/lair.db",
    model_config_path: str | Path | None = None,
    model_gateway: ModelGateway | None = None,
) -> FastAPI:
    app = FastAPI(title="Lair Service", version="0.1.0")
    engine = create_database_engine(database_url)
    init_database(engine)
    session_factory = create_session_factory(engine)
    notes_service = NotesService(NotesRepository(session_factory))
    app.state.notes_service = notes_service
    configured_path = model_config_path or os.environ.get("OPENLAIR_CONFIG")
    app.state.model_gateway = model_gateway or create_model_gateway_from_config(configured_path)
    app.state.assistant_runtime = LangGraphAssistantRuntime(model_gateway=app.state.model_gateway, workspace_path=".")
    app.include_router(router)
    return app


app = create_app()
