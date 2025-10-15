import streamlit as st
import openai
import json
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. API Key and Client Configuration ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
    TWELVE_DATA_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]
    FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"] 
except KeyError as e:
    st.error(f"ERROR: The secret key '{e.args[0]}' was not found.")
    st.info("Please update your secrets file with your OPENAI, POLYGON, TWELVE_DATA, and FINNHUB API keys.")
    st.stop()

# Initialize clients and base URLs
client = openai.OpenAI(api_key=OPENAI_API_KEY)
import finnhub
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
POLYGON_BASE_URL = 'https://api.polygon.io'
TD_BASE_URL = 'https://api.twelvedata.com'

# --- 2. Tool Functions with Optimized API Strategy ---

def get_stock_price_and_vwap(ticker_symbol: str):
    """Gets the previous day's closing price, change, and Volume Weighted Average Price (VWAP) from Polygon.io."""
    try:
        ticker_symbol = ticker_symbol.upper()
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker_symbol}/prev"
        params = {'apiKey': POLYGON_API_KEY}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("resultsCount", 0) == 0:
            return json.dumps({"error": f"No previous day data found for {ticker_symbol} on Polygon.io."})
        
        result = data['results'][0]
        return json.dumps({
            "ticker": data['ticker'],
            "close": result['c'],
            "high": result['h'],
            "low": result['l'],
            "open": result['o'],
            "volume": result['v'],
            "vwap": result.get('vw'), # VWAP is included in this endpoint
            "change": result['c'] - result['o'], # Calculate change
            "percent_change": ((result['c'] - result['o']) / result['o']) * 100
        })
    except Exception as e:
        return json.dumps({"error": f"An error occurred with Polygon.io price check: {str(e)}"})

def get_company_news(ticker_symbol: str):
    """Gets the latest news with sentiment analysis from Finnhub."""
    try:
        ticker_symbol = ticker_symbol.upper()
        today = datetime.now().strftime('%Y-%m-%d')
        one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        news = finnhub_client.company_news(ticker_symbol, _from=one_week_ago, to=today)
        if not news:
            return json.dumps({"message": "No recent news found from Finnhub."})
        return json.dumps([{'headline': article['headline'], 'summary': article['summary']} for article in news[:5]])
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred while fetching news from Finnhub: {str(e)}"})

def get_candlestick_chart(ticker_symbol: str):
    """Gets historical data from Polygon.io to display as a chart."""
    try:
        ticker_symbol = ticker_symbol.upper()
        today = datetime.now()
        one_year_ago = today - timedelta(days=365)
        url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker_symbol}/range/1/day/{one_year_ago.strftime('%Y-%m-%d')}/{today.strftime('%Y-%m-%d')}"
        params = {'apiKey': POLYGON_API_KEY}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "OK" or data.get("resultsCount", 0) == 0:
            return json.dumps({"error": "No historical data found on Polygon.io for this ticker."})
        
        df = pd.DataFrame(data['results'])
        df['time'] = pd.to_datetime(df['t'], unit='ms')
        df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
        df = df.sort_index()

        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(title=f'{ticker_symbol} Candlestick Chart (Data from Polygon.io)', xaxis_title='Date', yaxis_title='Price (USD)', xaxis_rangeslider_visible=False, template='plotly_dark')
        
        return json.dumps({"display_plotly_chart": True, "chart_json": fig.to_json()})
    except Exception as e:
        return json.dumps({"error": f"An error occurred with Polygon.io charting: {str(e)}"})

def get_technical_analysis(ticker_symbol: str):
    """Gets a summary of key technical indicators (RSI, MACD, EMA, ADX) from Twelve Data."""
    try:
        ticker_symbol = ticker_symbol.upper()
        indicators = ['RSI', 'MACD', 'EMA', 'ADX']
        results = {}
        for indicator in indicators:
            params = {
                'symbol': ticker_symbol, 'interval': '1day', 'apikey': TWELVE_DATA_API_KEY,
                'outputsize': 1 # We only need the latest value
            }
            # Add specific parameters for each indicator
            if indicator == 'MACD':
                params['fast_period'] = 12
                params['slow_period'] = 26
                params['signal_period'] = 9

            response = requests.get(f"{TD_BASE_URL}/{indicator.lower()}", params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok" and data.get("values"):
                latest_point = data['values'][0]
                results[indicator] = {k: round(float(v), 2) for k, v in latest_point.items() if k != 'datetime'}
        
        if not results:
            return json.dumps({"error": "Could not retrieve any technical indicators from Twelve Data."})
            
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": f"An error occurred during technical analysis with Twelve Data: {str(e)}"})

# --- 3. OpenAI Tool and Model Configuration (Optimized) ---
tools = [
    {"type": "function", "function": {"name": "get_stock_price_and_vwap", "description": "Get the latest stock price and VWAP from Polygon.io.", "parameters": {"type": "object", "properties": {"ticker_symbol": {"type": "string"}}, "required": ["ticker_symbol"]}}},
    {"type": "function", "function": {"name": "get_company_news", "description": "Get the latest news for a company from Finnhub.", "parameters": {"type": "object", "properties": {"ticker_symbol": {"type": "string"}}, "required": ["ticker_symbol"]}}},
    {"type": "function", "function": {"name": "get_candlestick_chart", "description": "Display an interactive candlestick chart from Polygon.io.", "parameters": {"type": "object", "properties": {"ticker_symbol": {"type": "string"}}, "required": ["ticker_symbol"]}}},
    {"type": "function", "function": {"name": "get_technical_analysis", "description": "Get key technical indicators (RSI, MACD, EMA, ADX) for a stock from Twelve Data.", "parameters": {"type": "object", "properties": {"ticker_symbol": {"type": "string"}}, "required": ["ticker_symbol"]}}},
]
MODEL = "gpt-4o"
available_functions = {
    "get_stock_price_and_vwap": get_stock_price_and_vwap,
    "get_company_news": get_company_news,
    "get_candlestick_chart": get_candlestick_chart,
    "get_technical_analysis": get_technical_analysis,
}

# --- 4 & 5. Streamlit UI and Chat Logic ---
st.set_page_config(page_title="AI Financial Co-pilot", page_icon="📈", layout="wide")
st.title("📈 AI Financial Co-pilot")
st.caption("Optimized with Polygon.io, Twelve Data, and Finnhub. How can I help?")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] != "tool" and message.get("content"):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Ask about a stock..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            api_messages = [msg for msg in st.session_state.messages if msg.get("content") is not None or msg.get("tool_calls")]
            response = client.chat.completions.create(
                model=MODEL, messages=api_messages, tools=tools, tool_choice="auto",
            )
            response_message = response.choices[0].message
            st.session_state.messages.append(response_message.model_dump(exclude_unset=True))

            if response_message.tool_calls:
                tool_outputs = []
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    st.write(f"🤖 Calling `{function_name}`...")
                    function_response_str = function_to_call(**function_args)
                    
                    try:
                        response_data = json.loads(function_response_str)
                        if isinstance(response_data, dict):
                            if error_message := response_data.get("error"):
                                st.error(f"API Error for `{function_name}`: {error_message}")
                            
                            elif response_data.get("display_plotly_chart"):
                                fig_json = response_data["chart_json"]
                                fig = go.Figure(json.loads(fig_json))
                                st.plotly_chart(fig, use_container_width=True)

                    except (json.JSONDecodeError, TypeError):
                        pass

                    tool_outputs.append({
                        "tool_call_id": tool_call.id, "role": "tool",
                        "name": function_name, "content": function_response_str,
                    })
                
                st.session_state.messages.extend(tool_outputs)
                second_response = client.chat.completions.create(model=MODEL, messages=st.session_state.messages)
                final_response_message = second_response.choices[0].message
                st.markdown(final_response_message.content)
                st.session_state.messages.append(final_response_message.model_dump(exclude_unset=True))
            else:
                st.markdown(response_message.content)

