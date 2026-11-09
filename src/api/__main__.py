import uvicorn

from ..infrastructure.config import load_settings

if __name__ == "__main__":
    s = load_settings()
    uvicorn.run("src.api.main:app", host=s.api_host, port=s.api_port)
