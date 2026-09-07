from fastapi import FastAPI


def create_api() -> FastAPI:
    application = FastAPI(
        title="GenStim AI",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_api()
