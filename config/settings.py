"""
settings.py
Centralized configuration file.
- Stores Supabase URL and Key.
- Keeps constants like segment IDs, polling intervals.
- Imported by all service modules.
"""

# Supabase configuration
SUPABASE_URL = "https://pepntaxswvtgdiebjdta.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBlcG50YXhzd3Z0Z2RpZWJqZHRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4ODcwMjksImV4cCI6MjA3MjQ2MzAyOX0.tsY6JnxG5jKUJT1F_6BLhZWIxvLTuzE9GeUBNmKnfWo"

# Trading constants
SEGMENT_NSEFO = 2   # Segment ID for NSE Futures & Options
POLL_INTERVAL = 2   # Seconds between LTP checks in monitor.py

# Logging tables
TABLE_ENABLED_CLIENTS = "enabled_clients"
TABLE_RESEARCH_CALLS = "research_calls"
TABLE_POSITIONS = "positions"
TABLE_ORDER_LOGS = "order_logs"
TABLE_PROGRAM_LOGS = "program_logs"


# # # Static IP Proxy
# # STATIC_IP_HOST = "dc-mum-005.staticip.in"
# # STATIC_IP_PORT = 443
# #
# # STATIC_IP_USERNAME = "Jk8Kbqe2Nny7Un0tyMRCyy"
# # STATIC_IP_PASSWORD = "a414c2bb65b14303864398ca095803eb"
# #
# # PROXIES = {
# #     "http": f"http://{STATIC_IP_USERNAME}:{STATIC_IP_PASSWORD}@{STATIC_IP_HOST}:{STATIC_IP_PORT}",
# #     "https": f"http://{STATIC_IP_USERNAME}:{STATIC_IP_PASSWORD}@{STATIC_IP_HOST}:{STATIC_IP_PORT}"
# # }

# import requests
#
# STATIC_IP_HOST = "dc-mum-005.staticip.in"
# STATIC_IP_PORT = 443
#
# STATIC_IP_USERNAME = "Jk8Kbqe2Nny7Un0tyMRCyy"
# STATIC_IP_PASSWORD = "a414c2bb65b14303864398ca095803eb"
#
# PROXIES = {
#     "http": f"http://{STATIC_IP_USERNAME}:{STATIC_IP_PASSWORD}@{STATIC_IP_HOST}:{STATIC_IP_PORT}",
#     "https": f"http://{STATIC_IP_USERNAME}:{STATIC_IP_PASSWORD}@{STATIC_IP_HOST}:{STATIC_IP_PORT}"
# }
#
# try:
#     r = requests.get(
#         "https://api.ipify.org?format=json",
#         proxies=PROXIES,
#         timeout=15
#     )
#     print(r.text)
# except Exception as e:
#     print("ERROR:", repr(e))