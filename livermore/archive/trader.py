#https://pypi.org/project/websocket_client/
import websocket
import json


def on_message(ws, message):
    """Callback function triggered when a message is received."""
    data = json.loads(message)
    print("Received Data:", data)

def on_error(ws, error):
    """Callback function triggered on error."""
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    """Callback function triggered when the connection is closed."""
    print("Connection closed")

def on_open(ws):
    """Callback function triggered when the connection is opened."""
    # Subscribe to a symbol (e.g., AAPL for Apple stock)
    subscribe_message = json.dumps({
        "type": "subscribe",
        "symbol": "AAPL"
    })
    ws.send(subscribe_message)
    print("Subscribed to AAPL")

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://ws.finnhub.io?token=cu9bivpr01qnf5nmlh8gcu9bivpr01qnf5nmlh90",
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()