"""
client_market_details.py
Market data utilities.
- fetch_ltp: Polling API call to get LTP (simple, current method).
- subscribe_ltp: WebSocket subscription for real-time ticks (future upgrade).
- get_order_book_df: Fetch order book.
- get_master: Fetch master contracts.
- fetch_ohlc: Fetch OHLC candles.
"""

import json
import pandas as pd


def fetch_ltp(market_bt, segment: int, token: int):
    """
    Fetch the Last Traded Price (LTP) for a given instrument via API polling.
    market_bt: Market_Xt client
    segment: exchange segment (e.g., 2 for NSEFO)
    token: instrument token
    """
    instruments = [{"exchangeSegment": int(segment), "exchangeInstrumentID": int(token)}]
    response = market_bt.get_quote(
        Instruments=instruments,
        xtsMessageCode=1502,
        publishFormat='JSON'
    )
    if response.get("type") == "error":
        print("[fetch_ltp] API error:", response.get("description", response.get("message")))
        return None

    result = response.get("result", {})
    listQuotes = result.get("listQuotes") or []
    if not listQuotes:
        return None

    raw = listQuotes[0]
    obj = json.loads(raw) if isinstance(raw, str) else raw
    touch = obj.get("Touchline", {})
    ltp = touch.get("LastTradedPrice")
    return float(ltp) if ltp is not None else None


def subscribe_ltp(market_bt, tokens, callback):
    """
    Subscribe to LTP via WebSocket (future upgrade).
    market_bt: Market_Xt client with WebSocket support.
    tokens: list of instrument tokens to subscribe.
    callback: function to handle tick data (e.g., update dict).

    Example usage:
        def on_tick(data):
            print("Tick:", data)
        subscribe_ltp(market_bt, [123456], on_tick)
    """
    instruments = [{"exchangeSegment": 2, "exchangeInstrumentID": int(t)} for t in tokens]
    market_bt.subscribe(
        Instruments=instruments,
        xtsMessageCode=1502,
        publishFormat='JSON',
        callback=callback
    )
    print("[subscribe_ltp] Subscribed to tokens:", tokens)


def get_order_book_df(interactive_bt, client_id: str):
    """
    Fetch the order book and return it as a DataFrame-like structure.
    interactive_bt: Interactive_Xt client
    """
    resp = interactive_bt.get_order_book()
    if resp.get("type") != "success":
        raise RuntimeError(f"Order book fetch failed: {resp}")
    return resp["result"]


def get_master(market_bt, segments=None):
    if segments is None:
        segments = ["2"]
    resp = market_bt.get_master(exchangeSegmentList=segments)
    if resp.get("type") != "success":
        raise RuntimeError(f"Master fetch failed: {resp}")

    result = resp["result"]

    if isinstance(result, dict) and "data" in result:
        return result["data"]
    if isinstance(result, str):
        return result.strip().split("\n")

    raise RuntimeError("Unexpected master format")


def fetch_ohlc(market_bt, exchange_segment, token, start_time, end_time, compression=3):
    """
    Fetch OHLC candles for a given instrument.
    """
    resp = market_bt.get_ohlc(
        exchangeSegment=exchange_segment,
        exchangeInstrumentID=token,
        startTime=start_time,
        endTime=end_time,
        compressionValue=compression
    )

    if resp.get("type") != "success":
        raise Exception("OHLC fetch failed")

    data = resp["result"]["dataReponse"]
    rows = data.split(",")
    parsed = []

    for row in rows:
        if not row.strip():
            continue
        values = row.split("|")
        parsed.append({
            "timestamp": int(values[0]),
            "open": float(values[1]),
            "high": float(values[2]),
            "low": float(values[3]),
            "close": float(values[4])
        })

    return pd.DataFrame(parsed)
