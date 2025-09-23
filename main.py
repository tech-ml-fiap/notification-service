from fastapi import FastAPI
from app.adapters.driver.controllers.notification_controller import router as notification_router

def create_app() -> FastAPI:
    app = FastAPI(title="Notification Service")
    app.include_router(notification_router, tags=["notifications"])
    return app

app = create_app()
