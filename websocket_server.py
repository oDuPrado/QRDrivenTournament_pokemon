import asyncio
import websockets

class WebSocketServer:
    """
    A WebSocket server to handle client connections and broadcast messages.
    """
    def __init__(self, host="localhost", port=8765):
        """
        Initializes the WebSocket server.

        Args:
            host (str): The hostname or IP to bind the server. Default is "localhost".
            port (int): The port to bind the server. Default is 8765.
        """
        self.host = host
        self.port = port
        self.clients = set()  # Set of connected clients

    async def register(self, websocket):
        """
        Registers a new client connection.

        Args:
            websocket: The WebSocket connection instance.
        """
        self.clients.add(websocket)
        print(f"New client connected: {websocket.remote_address}")
        try:
            # Wait until the client disconnects
            await websocket.wait_closed()
        finally:
            # Remove client when disconnected
            self.clients.remove(websocket)
            print(f"Client disconnected: {websocket.remote_address}")

    async def broadcast(self, message):
        """
        Broadcasts a message to all connected clients.

        Args:
            message (str): The message to send.
        """
        if self.clients:  # Only broadcast if there are clients
            await asyncio.gather(*[client.send(message) for client in self.clients])

    async def handler(self, websocket):
        """
        Handles incoming WebSocket connections.

        Args:
            websocket: The WebSocket connection instance.
        """
        await self.register(websocket)

    async def start(self):
        """
        Starts the WebSocket server and keeps it running.
        """
        print(f"WebSocket server started at ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # Keeps the server running indefinitely
