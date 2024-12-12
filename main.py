import asyncio
import os
import qrcode
import threading
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from websocket_server import WebSocketServer
import json

# Flask app configuration
app = Flask(__name__, template_folder='templates', static_folder='static')

# Match outcomes dictionary
outcome = {
    0: "Playing",
    1: "Player 1 Wins",
    2: "Player 2 Wins",
    3: "Tie",
    10: "Double Loss",
}

# Tournament category levels
category = {
    'Junior': 0,
    'Senior': 1,
    'Master': 2,
}

# Global variables
global_websocket_server = None  # WebSocket server instance
main_loop = None  # Asyncio event loop
results = {}  # Temporary storage for match results
last_processed_data = None  # Holds the last processed .tdf file data


@app.route("/")
def home():
    """Renders the main page."""
    return render_template("index.html")


@app.route("/mesa/<int:mesa_id>")
def mesa(mesa_id):
    """Renders the page for individual tables."""
    return render_template("mesa.html", mesa_id=mesa_id)


@app.route("/report.html")
def report_page():
    """Renders the report popup page."""
    return render_template("report.html")


@app.route("/get-results", methods=["GET"])
def get_results():
    """Returns the temporary results stored in memory."""
    return jsonify({"results": results})


async def broadcast_results():
    """Broadcasts updated results to WebSocket clients."""
    if global_websocket_server is not None:
        await global_websocket_server.broadcast(json.dumps({
            "type": "update_results",
            "results": results
        }))


@app.route("/report", methods=["POST"])
def report():
    """Handles the reporting of match results."""
    data = request.get_json()
    table_id = data.get("mesa_id")
    outcome = data.get("resultado")

    # Prevent overwriting an existing result unless cleared
    current = results.get(table_id, "Playing")
    if current != "Playing" and current != "No result reported":
        return jsonify({"message": "This table already has a final result. Use 'Incorrect Report' to change."}), 400

    results[table_id] = outcome
    print(f"Result for Table {table_id}: {outcome}")

    # Notify WebSocket clients
    asyncio.run_coroutine_threadsafe(broadcast_results(), main_loop)
    return jsonify({"message": f"Result for Table {table_id} recorded as '{outcome}'"})


@app.route("/clear-report", methods=["POST"])
def clear_report():
    """Clears the result for a specific table."""
    data = request.get_json()
    table_id = data.get("mesa_id")
    if table_id in results:
        del results[table_id]
    print(f"Report for Table {table_id} cleared.")
    asyncio.run_coroutine_threadsafe(broadcast_results(), main_loop)
    return jsonify({"message": f"Report for Table {table_id} cleared."})


@app.route("/clear-all-results", methods=["POST"])
def clear_all_results():
    """Clears all reported results."""
    results.clear()
    print("All results cleared.")
    asyncio.run_coroutine_threadsafe(broadcast_results(), main_loop)
    return jsonify({"message": "All results cleared."})


def run_flask():
    """Starts the Flask server."""
    app.run(host="0.0.0.0", port=5000, debug=False)


def generate_qr_codes(base_url, num_tables):
    """Generates QR codes for each table."""
    qr_code_dir = "qrcodes"
    os.makedirs(qr_code_dir, exist_ok=True)
    for table_id in range(1, num_tables + 1):
        url = f"{base_url}/mesa/{table_id}"
        qr = qrcode.make(url)
        qr_path = os.path.join(qr_code_dir, f"table_{table_id}.png")
        qr.save(qr_path)
        print(f"QR Code generated for Table {table_id}: {url}")


def get_latest_tdf(directory):
    """Finds the latest .tdf file in the specified directory."""
    tdf_files = [f for f in os.listdir(directory) if f.endswith('.tdf')]
    if not tdf_files:
        print("No .tdf files found in the directory.")
        return None
    latest_file = max(tdf_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    print(f"Latest .tdf file found: {latest_file}")
    return os.path.join(directory, latest_file)


class TDFHandler(FileSystemEventHandler):
    """Handles changes in .tdf files."""
    def __init__(self, directory, websocket_server, loop):
        self.directory = directory
        self.websocket_server = websocket_server
        self.loop = loop
        self.last_sent_data = None

    def on_created(self, event):
        """Triggered when a new .tdf file is created."""
        if event.src_path.endswith(".tdf"):
            print(f"New file created: {event.src_path}")
            self.process_file(get_latest_tdf(self.directory))

    def on_modified(self, event):
        """Triggered when an existing .tdf file is modified."""
        if event.src_path.endswith(".tdf"):
            print(f"File modified: {event.src_path}")
            self.process_file(get_latest_tdf(self.directory))

    def process_file(self, file_path):
        """Processes the .tdf file and broadcasts the data."""
        global last_processed_data
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = file.read()
            soup = BeautifulSoup(data, 'lxml')
            my_json = {'players': self.extract_players(soup), 'round': self.extract_rounds(soup)}
            last_processed_data = my_json
            print(f"Processed JSON:\n{json.dumps(my_json, indent=4, ensure_ascii=False)}")
        except Exception as e:
            print(f"Error processing file: {e}")

    def extract_players(self, soup):
        """Extracts player information from .tdf."""
        players = soup.find("players").find_all('player')
        return {p['userid']: f"{p.find('firstname').string} {p.find('lastname').string}" for p in players}

    def extract_rounds(self, soup):
        """Extracts round information from .tdf."""
        return {}


async def main_async():
    """Main asynchronous task for WebSocket and directory monitoring."""
    base_url = "<base_url>"  # Replace with your server's base URL
    num_tables = 10
    generate_qr_codes(base_url, num_tables)

    tdf_directory = "<tdf_directory>"  # Replace with your .tdf directory path
    global global_websocket_server, main_loop
    global_websocket_server = WebSocketServer()
    main_loop = asyncio.get_running_loop()

    monitor_task = asyncio.create_task(monitor_directory(tdf_directory, global_websocket_server))
    websocket_task = asyncio.create_task(global_websocket_server.start())

    await asyncio.gather(monitor_task, websocket_task)


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    asyncio.run(main_async())
