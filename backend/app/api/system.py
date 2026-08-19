"""系统级路由：存活/就绪探针 + Prometheus 指标（K8s 探针与监控用，不依赖业务服务）。

端点：
- GET /healthz/live  存活探针（livenessProbe）：进程活着即 ok，不依赖任何外部资源
- GET /healthz/ready 就绪探针（readinessProbe）：DB 可连接才就绪，失败返回 503 + 错误信息
- GET /metrics       Prometheus 指标：HTTP 请求指标自动采集（prometheus-fastapi-instrumentator）

探针不走业务统一信封（{code, message, data}），保持简单 JSON + HTTP 状态码，
这是 K8s / Prometheus 生态的约定，探针只按状态码判断。
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

router = APIRouter(tags=["system"])

# 全局 Instrumentator：在 create_app 中 instrument(app) 并 expose /metrics。
# 探针自身路径不计入指标，避免探针轮询频率污染监控数据。
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/healthz/live", "/healthz/ready"],
)


@router.get("/healthz/live")
async def liveness() -> dict:
    """存活探针：进程存活即返回 ok（不依赖 DB 等外部资源）。"""
    return {"status": "ok"}


@router.get("/healthz/ready")
async def readiness(request: Request) -> Response:
    """就绪探针：DB 可连接才返回就绪；不可用返回 503 并携带错误信息。"""
    try:
        with request.app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - 探针必须捕获所有异常并给出可读信息
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "detail": str(exc)},
        )
    return JSONResponse(status_code=200, content={"status": "ready"})
