import pandas as pd

from helper_funct.client_master_download import load_master


_master_df = None


def initialize_master(market_xt):
    global _master_df

    _master_df = load_master(market_xt)

    return _master_df


def get_master():
    global _master_df

    if _master_df is None:
        raise RuntimeError(
            "Master data is not initialized"
        )

    return _master_df


def get_symbols(instrument_type="OPTIONS", search=""):
    df = get_master().copy()

    print("\n========== MASTER DEBUG ==========")
    print("TOTAL ROWS:", len(df))
    print("COLUMNS:", df.columns.tolist())

    if "ExchangeSegment" in df.columns:
        print("\nEXCHANGE SEGMENTS:")
        print(df["ExchangeSegment"].value_counts(dropna=False))

    print("\nSAMPLE SYMBOLS:")
    print(df["Symbol"].head(20).tolist())

    instrument_type = str(instrument_type).upper()

    if instrument_type == "OPTIONS":
        df = df[
            df["ExchangeSegment"].astype(str).isin(
                ["2", "NSEFO", "NFO", "12", "BSEFO"]
            )
        ]

    elif instrument_type == "EQUITY":
        df = df[
            df["ExchangeSegment"].astype(str).isin(
                ["1", "NSECM", "NSE", "11", "BSECM"]
            )
        ]

    print("\nAFTER SEGMENT FILTER:", len(df))

    search = str(search).strip().upper()

    if search:
        df = df[
            df["Symbol"]
            .astype(str)
            .str.upper()
            .str.startswith(search)
        ]

    symbols = (
        df["Symbol"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    print("FINAL SYMBOL COUNT:", len(symbols))
    print("=================================\n")

    return symbols


def get_expiries(symbol):
    df = get_master().copy()

    if df.empty:
        return []

    symbol = str(symbol).strip().upper()

    # Filter symbol
    df = df[
        df["Symbol"].astype(str).str.upper() == symbol
    ].copy()

    if df.empty:
        return []

    # Convert expiry to datetime
    df["ExpiryDate"] = pd.to_datetime(
        df["Expiry"],
        errors="coerce"
    )

    # Remove invalid expiry values
    df = df.dropna(subset=["ExpiryDate"])

    # Get current datetime
    now = pd.Timestamp.now()

    # Keep only current/future expiries
    df = df[
        df["ExpiryDate"] >= now
    ]

    # Sort by actual date
    df = df.sort_values(
        "ExpiryDate"
    )

    # Format for frontend
    expiries = (
        df["ExpiryDate"]
        .dt.strftime("%d-%m-%Y %H:%M")
        .drop_duplicates()
        .tolist()
    )

    return expiries

def get_strikes(symbol, expiry):
    df = get_master().copy()

    df = df[
        df["Symbol"]
        .astype(str)
        .str.upper()
        == str(symbol).upper()
    ]

    df["ExpiryFormatted"] = pd.to_datetime(
        df["Expiry"],
        errors="coerce"
    ).dt.strftime("%d-%m-%Y %H:%M")

    df = df[
        df["ExpiryFormatted"] == expiry
    ]

    strikes = (
        pd.to_numeric(
            df["Strike"],
            errors="coerce"
        )
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return strikes


def get_option_contract(
    symbol,
    expiry,
    strike,
    option_type
):
    df = get_master().copy()

    df = df[
        df["Symbol"]
        .astype(str)
        .str.upper()
        == str(symbol).upper()
    ]

    df["ExpiryFormatted"] = pd.to_datetime(
        df["Expiry"],
        errors="coerce"
    ).dt.strftime("%d-%m-%Y %H:%M")

    df = df[
        df["ExpiryFormatted"] == expiry
    ]

    df = df[
        pd.to_numeric(
            df["Strike"],
            errors="coerce"
        ) == float(strike)
    ]

    option_type = str(option_type).upper()

    option_code = 3 if option_type == "CE" else 4

    df = df[
        pd.to_numeric(
            df["OptionType"],
            errors="coerce"
        ) == option_code
    ]

    if df.empty:
        return None

    row = df.iloc[0]

    segment = str(row["ExchangeSegment"]).upper()

    if segment in ["2", "NSEFO", "NFO"]:
        exchange_segment = "NSEFO"
    elif segment in ["12", "BSEFO"]:
        exchange_segment = "BSEFO"
    else:
        exchange_segment = segment

    return {
        "instrument_id": int(row["Token"]),
        "symbol": str(row["Symbol"]),
        "exchange_segment": exchange_segment,
        "multiplier": int(row["Multiplier"]),
        "tick_size": float(row["TickSize"]),
        "expiry": expiry,
        "strike": float(strike),
        "option_type": option_type
    }


def get_equity_contract(symbol):
    df = get_master().copy()

    symbol = str(symbol).strip().upper()

    # Match symbol
    df = df[
        df["Symbol"]
        .astype(str)
        .str.upper()
        == symbol
    ].copy()

    if df.empty:
        return None

    # Keep only NSECM / BSECM
    equity_df = df[
        df["ExchangeSegment"].astype(str).isin(
            [
                "1",
                "NSECM",
                "NSE",
                "11",
                "BSECM"
            ]
        )
    ].copy()

    if equity_df.empty:
        return None

    # Prefer NSECM if the symbol exists in both
    nse_df = equity_df[
        equity_df["ExchangeSegment"].astype(str).isin(
            ["1", "NSECM", "NSE"]
        )
    ]

    if not nse_df.empty:
        row = nse_df.iloc[0]
        exchange_segment = "NSECM"
    else:
        row = equity_df.iloc[0]
        exchange_segment = "BSECM"

    return {
        "instrument_id": int(row["Token"]),
        "symbol": str(row["Symbol"]),
        "exchange_segment": exchange_segment,
        "multiplier": 1,
        "lot_size": int(row["LotSize"]) if pd.notna(row["LotSize"]) else 1,
        "tick_size": float(row["TickSize"]),
    }