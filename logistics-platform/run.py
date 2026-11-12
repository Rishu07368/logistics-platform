from backend import config
from backend.app import create_app

if __name__ == "__main__":
    app = create_app()
    print(f"Logistics platform running at http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
