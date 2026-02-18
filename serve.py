from waitress import serve

from app import app
from config import Config


if __name__ == "__main__":
    cfg = Config()
    serve(app, host=cfg.HOST, port=cfg.PORT)

