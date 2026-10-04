import uvicorn

from grzyby_server.settings import settings

if __name__ == "__main__":
    uvicorn.run("grzyby_server.app:app", host=settings.host, port=settings.port, reload=False)
