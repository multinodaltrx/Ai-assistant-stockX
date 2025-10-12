# First, make sure you have installed the library: pip install websocket-client
import websocket
import json

# --- ACTION: INSERT YOUR API KEY HERE ---
YOUR_FINNHUB_API_KEY = "d3lnkuhr01qq28eo8q50d3lnkuhr01qq28eo8q5g"
# -----------------------------------------

def on_message(ws, message):
    """This function is called every time a new message is received from the WebSocket."""
    print("Received data:")
    print(message)

def on_error(ws, error):
    """This function is called when an error occurs."""
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    """This function is called when the connection is closed."""
    print("### Connection closed ###")

def on_open(ws):
    """This function is called once the connection is successfully opened."""
    print("Connection opened. Subscribing to AAPL trades...")
    # Subscribe to the trade feed for the AAPL stock ticker
    ws.send('{"type":"subscribe","symbol":"AAPL"}')

if __name__ == "__main__":
    # Enable detailed tracing for debugging if needed
    # websocket.enableTrace(True)

    # Construct the WebSocket URL with your API key
    ws_url = f"wss://ws.finnhub.io?token={YOUR_FINNHUB_API_KEY}"

    # Create the WebSocketApp object
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)

    # Start the connection and listen for messages forever
    print("Connecting to Finnhub WebSocket...")
    ws.run_forever()