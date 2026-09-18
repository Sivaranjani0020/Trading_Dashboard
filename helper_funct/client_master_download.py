"""
client_master_download.py

Handles daily master contract download and lookup
for both:
    - NSE Equity (NSECM)
    - NSE Futures & Options (NSEFO)

The master is downloaded once per day and saved locally.
"""

import os
from datetime import datetime

import pandas as pd


MASTER_FILE = "master_data.csv"
MASTER_DATE_FILE = "master_date.txt"


COLUMNS = [
    "ExchangeSegment",
    "Token",
    "LotSize",
    "Symbol",
    "DisplayName",
    "InstrumentType",
    "Series",
    "ISIN",
    "LastTradedPrice",
    "Change",
    "OpenInterest",
    "TickSize",
    "Multiplier",
    "Decimals",
    "UniqueId",
    "Underlying",
    "Expiry",
    "Strike",
    "OptionType",
    "Description",
    "Active",
    "Tradable",
    "SymbolName"
]

NSECM_COLUMNS = [
    "ExchangeSegment",
    "Token",
    "LotSize",
    "Symbol",
    "DisplayName",
    "InstrumentType",
    "Series",
    "ISIN",
    "LastTradedPrice",
    "Change",
    "OpenInterest",
    "TickSize",
    "Multiplier",
    "Decimals",
    "UniqueId",
    "Underlying",
    "Expiry",
    "Strike",
    "Description",
    "Active",
    "Tradable",
    "SymbolName"
]

def download_master(market_xt):
    """
    Download master contracts for:
        - NSECM
        - NSEFO

    NSECM and NSEFO have different field structures,
    so they are parsed separately and then combined.
    """

    print("\nDownloading master:")

    print("NSECM constant:", market_xt.EXCHANGE_NSECM)
    print("NSEFO constant:", market_xt.EXCHANGE_NSEFO)

    resp = market_xt.get_master(
        exchangeSegmentList=[
            market_xt.EXCHANGE_NSECM,
            market_xt.EXCHANGE_NSEFO
        ]
    )

    print("\n========== RAW MASTER DEBUG ==========")
    print("Response type:", resp.get("type"))

    result_data = resp.get("result", "")

    print("Result length:", len(result_data))
    print("First 500 characters:")
    print(result_data[:500])

    print("======================================\n")

    if resp.get("type") != "success":
        print(
            f"Failed to download: "
            f"{resp.get('message', 'Unknown error')}"
        )
        raise Exception("Master download failed")

    if not result_data:
        raise Exception(
            "Master download failed: No data returned"
        )

    rows = result_data.strip().split("\n")

    nsecm_data = []
    nsefo_data = []

    for row in rows:

        fields = row.split("|")

        if fields[0] == market_xt.EXCHANGE_NSECM:

            if len(fields) == len(NSECM_COLUMNS):
                nsecm_data.append(fields)

        elif fields[0] == market_xt.EXCHANGE_NSEFO:

            if len(fields) == len(COLUMNS):
                nsefo_data.append(fields)

    print("NSECM valid rows:", len(nsecm_data))
    print("NSEFO valid rows:", len(nsefo_data))

    if not nsecm_data and not nsefo_data:
        raise Exception(
            "Master download failed: "
            "No valid data received"
        )

    # Create separate DataFrames

    nsecm_df = pd.DataFrame(
        nsecm_data,
        columns=NSECM_COLUMNS
    )

    nsefo_df = pd.DataFrame(
        nsefo_data,
        columns=COLUMNS
    )

    # Add OptionType column to NSECM
    # NSECM does not have option type.
    nsecm_df["OptionType"] = None

    # Make sure both DataFrames have the same columns
    nsecm_df = nsecm_df[COLUMNS]

    nsefo_df = nsefo_df[COLUMNS]

    # Combine NSECM + NSEFO
    df = pd.concat(
        [nsecm_df, nsefo_df],
        ignore_index=True
    )

    # Convert numeric columns
    df["Token"] = pd.to_numeric(
        df["Token"],
        errors="coerce"
    )

    df["LotSize"] = pd.to_numeric(
        df["LotSize"],
        errors="coerce"
    )

    df["Multiplier"] = pd.to_numeric(
        df["Multiplier"],
        errors="coerce"
    )

    df["TickSize"] = pd.to_numeric(
        df["TickSize"],
        errors="coerce"
    )

    df["Strike"] = pd.to_numeric(
        df["Strike"],
        errors="coerce"
    )

    # Convert expiry
    # NSECM expiry will be empty/NaN.
    df["Expiry"] = pd.to_datetime(
        df["Expiry"],
        errors="coerce"
    )

    # Save combined master
    df.to_csv(
        MASTER_FILE,
        index=False
    )

    print(
        f"\nMaster downloaded successfully: "
        f"{len(df)} rows"
    )

    print("\nExchange segments:")

    print(
        df["ExchangeSegment"]
        .value_counts()
    )

    # Save today's date
    with open(
        MASTER_DATE_FILE,
        "w"
    ) as f:
        f.write(
            datetime.now().strftime("%Y-%m-%d")
        )

    return df

def load_master(market_xt=None):
    """
    Load today's master.

    If today's master does not exist,
    download a fresh one.
    """

    today = datetime.now().strftime("%Y-%m-%d")

    if (
        not os.path.exists(MASTER_FILE)
        or not os.path.exists(MASTER_DATE_FILE)
    ):

        if market_xt is None:
            raise FileNotFoundError(
                "Master data not found and Market session unavailable"
            )

        return download_master(market_xt)

    with open(
        MASTER_DATE_FILE,
        "r"
    ) as file:
        saved_date = file.read().strip()

    if saved_date != today:

        if market_xt is None:
            raise RuntimeError(
                "Master data is outdated and Market session unavailable"
            )

        return download_master(market_xt)

    df = pd.read_csv(
        MASTER_FILE
    )

    df["Token"] = pd.to_numeric(
        df["Token"],
        errors="coerce"
    )

    df["LotSize"] = pd.to_numeric(
        df["LotSize"],
        errors="coerce"
    )

    df["Multiplier"] = pd.to_numeric(
        df["Multiplier"],
        errors="coerce"
    )

    df["TickSize"] = pd.to_numeric(
        df["TickSize"],
        errors="coerce"
    )

    df["Strike"] = pd.to_numeric(
        df["Strike"],
        errors="coerce"
    )

    df["Expiry"] = pd.to_datetime(
        df["Expiry"],
        errors="coerce"
    )

    return df


def get_option_contract_by_date(
    df,
    symbol,
    strike,
    callput,
    expiry_date
):
    """
    Find a specific option contract.
    """

    if isinstance(callput, str):

        option_type = (
            3
            if callput.upper() == "CE"
            else 4
        )

    else:
        option_type = int(callput)

    filtered = df[
        df["Symbol"]
        .astype(str)
        .str.upper()
        == str(symbol).upper()
    ]

    filtered = filtered[
        pd.to_numeric(
            filtered["Strike"],
            errors="coerce"
        )
        == float(strike)
    ]

    filtered = filtered[
        pd.to_numeric(
            filtered["OptionType"],
            errors="coerce"
        )
        == option_type
    ]

    if filtered.empty:
        return None

    filtered = filtered.copy()

    filtered["ExpiryDate"] = (
        pd.to_datetime(
            filtered["Expiry"],
            errors="coerce"
        )
        .dt.strftime("%d-%m-%Y %H:%M")
    )

    filtered = filtered[
        filtered["ExpiryDate"]
        == expiry_date
    ]

    if filtered.empty:
        return None

    return filtered.iloc[0].to_dict()


def get_multiplier_by_token(
    df,
    token
):
    contract = df[
        pd.to_numeric(
            df["Token"],
            errors="coerce"
        )
        == int(token)
    ]

    if contract.empty:
        raise Exception(
            f"Token not found: {token}"
        )

    return int(
        contract.iloc[0]["Multiplier"]
    )


def get_tick_size_by_token(
    df,
    token
):
    contract = df[
        pd.to_numeric(
            df["Token"],
            errors="coerce"
        )
        == int(token)
    ]

    if contract.empty:
        raise Exception(
            f"Token not found: {token}"
        )

    return float(
        contract.iloc[0]["TickSize"]
    )