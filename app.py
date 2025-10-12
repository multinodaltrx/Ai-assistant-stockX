# app.py

import streamlit as st
import openai
import finnhub
import json

# --- 1. API Key and Client Configuration ---

# Correctly load API keys from Streamlit's secrets management
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]
except KeyError as e:
    st.error(f"ERROR: The secret key '{e.args[0]}' was not found in your secrets file.")
    st.info("Please make sure your .streamlit/secrets.toml file contains your OPENAI_API_KEY and FINNHUB_API_KEY.")
    st.stop()

# Configure the OpenAI client
try:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# Configure the Finnhub client
try:
    finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Finnhub client: {e}")
    st.stop()

# --- 2. The "Tool" Definition (The Python function the AI can call) ---

def get_stock_price(ticker_symbol: str):
    """
    Gets the latest stock price for a given ticker symbol using the Finnhub API.
    Args:
        ticker_symbol: The stock ticker symbol (e.g., "AAPL", "GOOG").
    Returns:
        A JSON string with the current price, change, and other details,
        or an error message if the ticker is not found.
    """
    try:
        quote = finnhub_client.quote(ticker_symbol)
        if quote.get('c') == 0 and quote.get('d') is None:
            return json.dumps({"error": f"No data found for ticker: {ticker_symbol}."})
        
        price_data = {
            "ticker": ticker_symbol, "current_price": quote.get('c'), "change": quote.get('d'),
            "percent_change": quote.get('dp'), "high_price_today": quote.get('h'), "low_price_today": quote.get('l'),
        }
        return json.dumps(price_data)
    except Exception as e:
        return json.dumps({"error": f"An API error occurred: {str(e)}"})

# --- 3. OpenAI Tool and Model Configuration ---

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the latest stock price for a specific ticker symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker_symbol": {"type": "string", "description": "The stock ticker symbol, e.g., NVDA for NVIDIA."},
                },
                "required": ["ticker_symbol"],
            },
        },
    }
]
MODEL = "gpt-4o"

# --- 4. Streamlit UI Setup ---

st.set_page_config(page_title="AI Stock Assistant (GPT)", page_icon="📈")
st.title("📈 AI Stock Assistant (GPT)")
st.caption("Ask me for the latest stock prices! (e.g., 'What is the price of NVDA?')")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    # Don't display tool messages or assistant messages without content
    if message["role"] != "tool" and message.get("content"):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- 5. Main Chat Logic for OpenAI ---

if prompt := st.chat_input("What is the price of..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # *** THE FIX: Create a clean version of the history for the API call ***
            # This removes any messages where 'content' is None, which causes the error.
            api_messages = [msg for msg in st.session_state.messages if msg.get("content") is not None or msg.get("tool_calls")]
            
            # First API Call
            response = client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                tools=tools,
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            st.session_state.messages.append(response_message.model_dump(exclude_unset=True))

            if response_message.tool_calls:
                st.write("🤖 Calling Finnhub API...")
                function_name = response_message.tool_calls[0].function.name
                function_args = json.loads(response_message.tool_calls[0].function.arguments)
                function_response = get_stock_price(ticker_symbol=function_args.get("ticker_symbol"))

                st.session_state.messages.append(
                    {"tool_call_id": response_message.tool_calls[0].id, "role": "tool", "name": function_name, "content": function_response}
                )

                # Second API Call, using the full history
                second_response = client.chat.completions.create(
                    model=MODEL,
                    messages=st.session_state.messages,
                )
                final_response_message = second_response.choices[0].message
                st.markdown(final_response_message.content)
                st.session_state.messages.append(final_response_message.model_dump(exclude_unset=True))
            else:
                st.markdown(response_message.content)

