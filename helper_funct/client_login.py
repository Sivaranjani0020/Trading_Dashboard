"""
client_login.py
Handles login for Interactive and Market APIs with daily token reuse.
- Fetches credentials from Supabase.
- Reuses stored tokens if valid for today.
- Performs fresh login if no valid token.
- Updates Supabase with new tokens.
- Logs all login actions into program_logs.
"""

from helper_funct.Connect import XTSConnect
# import supabase
from datetime import datetime
# from config.settings import SUPABASE_URL, SUPABASE_KEY
from services.logger import log_program_event

# Supabase client setup
# supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
from database import (
    get_client_credentials,
    update_client_tokens
)
def fetch_credentials(client_id: str):
    creds = get_client_credentials(client_id)

    if not creds:
        raise ValueError(
            f"No credentials found for client_id={client_id}"
        )

    return creds

def login_xts(client_id: str):
    """
    Login manager with daily token reuse.
    Returns dict {Interactive_Xt, Market_Xt}.
    """
    creds = fetch_credentials(client_id)
    proxies = {
        "http": f"http://{creds['static_ip_username']}:{creds['static_ip_password']}@{creds['static_ip_host']}:{creds['static_ip_port']}",
        "https": f"http://{creds['static_ip_username']}:{creds['static_ip_password']}@{creds['static_ip_host']}:{creds['static_ip_port']}",
    }
    today = datetime.now().strftime("%Y-%m-%d")

    stored_interactive_token = creds.get("interactive_token")
    stored_market_token = creds.get("market_token")
    stored_date = creds.get("token_date")

    # ============================================
    # REUSE TOKENS
    # ============================================
    if stored_interactive_token and stored_market_token and stored_date == today:
        # log_program_event("Using stored tokens", details={"client_id": client_id})

        interactive_xt = XTSConnect(
            creds["interactive_api_key"],
            creds["interactive_api_secret"],
            "WEBAPI",
            proxies=proxies,
        )
        market_xt = XTSConnect(
            creds["market_api_key"],
            creds["market_api_secret"],
            "WEBAPI",
            proxies=proxies,
        )

        # Restore sessions
        interactive_xt._set_common_variables(stored_interactive_token, str(client_id), True)
        market_xt._set_common_variables(stored_market_token, str(client_id), False)

        return {"Interactive_Xt": interactive_xt, "Market_Xt": market_xt}
        # return {"Market_Xt": market_xt}
    # ============================================
    # FRESH LOGIN
    # ============================================
    log_program_event("Performing fresh login", details={"client_id": client_id})

    interactive_xt = XTSConnect(
        creds["interactive_api_key"],
        creds["interactive_api_secret"],
        "WEBAPI",
        proxies=proxies,
    )
    market_xt = XTSConnect(
        creds["market_api_key"],
        creds["market_api_secret"],
        "WEBAPI",
        proxies=proxies,
    )

    resp_interactive = interactive_xt.interactive_login()
    print("interactive login",resp_interactive)
    resp_market = market_xt.marketdata_login()
    print("market login",resp_market)
    if resp_interactive.get("type") != "success":
        log_program_event("Interactive login failed", details={"client_id": client_id, "resp": resp_interactive})
        raise RuntimeError("Interactive login failed")
    if resp_market.get("type") != "success":
        log_program_event("Market login failed", details={"client_id": client_id, "resp": resp_market})
        raise RuntimeError("Market login failed")

    # Extract tokens
    interactive_token = resp_interactive["result"]["token"]
    market_token = resp_market["result"]["token"]

    # Save tokens in Supabase
    update_client_tokens(
        client_id,
        interactive_token,
        market_token,
        today
    )

    log_program_event(
        "Tokens updated in SQLite",
        details={"client_id": client_id}
    )

    return {"Interactive_Xt": interactive_xt, "Market_Xt": market_xt}
    # return {"Market_Xt": market_xt}

# from datetime import datetime
# import supabase
# from helper_funct.Connect import XTSConnect
# from datetime import datetime
# # Initialize Supabase client once
# supabase_url = "https://pepntaxswvtgdiebjdta.supabase.co"
# supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBlcG50YXhzd3Z0Z2RpZWJqZHRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4ODcwMjksImV4cCI6MjA3MjQ2MzAyOX0.tsY6JnxG5jKUJT1F_6BLhZWIxvLTuzE9GeUBNmKnfWo"
#
# supabase_client = supabase.create_client(
#     supabase_url,
#     supabase_key
# )
#
#
# def fetch_credentials(client_id: str):
#     client_id = client_id.strip()
#
#     response = (
#         supabase_client
#         .table("xt_login_credentials")
#         .select("*")
#         .eq("client_id", client_id)
#         .execute()
#     )
#
#     print("[DEBUG] Supabase raw response:", response,datetime.now().strftime("%H:%M:%S.%f"))
#
#     if not response.data:
#         raise ValueError(f"No credentials found for client_id={client_id}")
#
#     return response.data[0]
#
#
# def login_xts(client_id: str):
#     """
#     Login manager with daily token reuse.
#     """
#
#     creds = fetch_credentials(client_id)
#
#     # Create clients
#     interactive_xt = XTSConnect(
#         creds["interactive_api_key"],
#         creds["interactive_api_secret"],
#         "WEBAPI",
#         proxy=creds["fixie_url"]
#     )
#
#     market_xt = XTSConnect(
#         creds["market_api_key"],
#         creds["market_api_secret"],
#         "WEBAPI",
#         proxy=creds["fixie_url"]
#     )
#     today = datetime.now().strftime("%Y-%m-%d")
#
#     stored_interactive_token = creds.get("interactive_token")
#     stored_market_token = creds.get("market_token")
#     stored_date = creds.get("token_date")
#
#     # ============================================
#     # REUSE TOKENS
#     # ============================================
#
#     if (
#             stored_interactive_token and
#             stored_market_token and
#             stored_date == today
#     ):
#         print(f"[DEBUG] Using stored tokens for {client_id}")
#
#         # Properly restore session
#         interactive_xt._set_common_variables(
#             stored_interactive_token,
#             str(client_id),
#             True
#         )
#
#         market_xt._set_common_variables(
#             stored_market_token,
#             str(client_id),
#             False
#         )
#
#         return {
#             "Interactive_Xt": interactive_xt,
#             "Market_Xt": market_xt
#         }
#     # ============================================
#     # FRESH LOGIN
#     # ============================================
#
#     print(f"[DEBUG] Performing fresh login for {client_id}",datetime.now().strftime("%H:%M:%S.%f"))
#
#     resp_interactive = interactive_xt.interactive_login()
#     resp_market = market_xt.marketdata_login()
#
#     print("Interactive login response:", resp_interactive,datetime.now().strftime("%H:%M:%S.%f"))
#     print("Market login response:", resp_market,datetime.now().strftime("%H:%M:%S.%f"))
#
#     if resp_interactive.get("type") != "success":
#         raise RuntimeError("Interactive login failed")
#
#     if resp_market.get("type") != "success":
#         raise RuntimeError("Market login failed")
#
#     # Extract tokens
#     interactive_token = resp_interactive["result"]["token"]
#     market_token = resp_market["result"]["token"]
#
#     # Save tokens in Supabase
#     (
#         supabase_client
#         .table("xt_login_credentials")
#         .update({
#             "interactive_token": interactive_token,
#             "market_token": market_token,
#             "token_date": today
#         })
#         .eq("client_id", client_id)
#         .execute()
#     )
#
#     print(f"[DEBUG] Tokens updated in Supabase for {client_id}")
#
#     return {
#         "Interactive_Xt": interactive_xt,
#         "Market_Xt": market_xt
#     }
#
# # if __name__ == "__main__":
# #     client_id = input("Please enter your client ID: ")
# #     login_xts(client_id)
