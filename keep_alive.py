from flask import Flask
from threading import Thread

app = Flask(__name__)


@app.route("/")
def home_page():
    return "Catastrophia Bot - keep_alive.py"


def run():
    print("Starting keep_alive server.")
    app.run(host='0.0.0.0', port=8080)


def start_server():
    """Runs the keep alive server in a separate thread."""

    server_thread = Thread(target=run)
    server_thread.start()
