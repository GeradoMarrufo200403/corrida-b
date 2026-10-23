from fastapi import FastAPI, Request
from sqlalchemy import text
from fastapi.responses import JSONResponse

from app.container import Container
from app.inventory.router import router as inventory_router
from app.orders.router import router as orders_router
from app.pricing.router import router as pricing_router
from app.shared.errors import DomainError


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(title="OrderFlow API", version="0.6")
    app.state.container = container or Container()

    @app.exception_handler(DomainError)
    def handle_domain_error(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code, content={"error": exc.code, "message": exc.message}
        )

    @app.get("/health", tags=["health"])
    def health():
        with app.state.container.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "up"}

    app.include_router(orders_router)
    app.include_router(inventory_router)
    app.include_router(pricing_router)
    return app


app = create_app()
