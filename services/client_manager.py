
"""
client_manager.py

Manages follower client sessions.
"""

from helper_funct.client_login import login_xts
from services.logger import log_program_event
from database import get_enabled_clients


def load_enabled_clients():
    """
    Fetch enabled clients from SQLite.
    Returns a list of client dictionaries.
    """
    clients = get_enabled_clients()

    log_program_event(
        "Loaded enabled clients",
        details={"count": len(clients)}
    )

    return clients


def login_clients(client_ids=None):
    """
    Perform login for all enabled clients or a provided list.
    Returns dict of client_id → session objects.
    """

    if client_ids is None:
        client_ids = load_enabled_clients()

    sessions = {}

    for client in client_ids:

        if isinstance(client, dict):
            cid = client["client_id"]
            lots = client.get("lots", 1)
        else:
            cid = client
            lots = 1

        try:
            session = login_xts(cid)

            session["lots"] = lots
            sessions[cid] = session

            log_program_event(
                "Client logged in",
                details={
                    "client_id": cid,
                    "lots": lots
                }
            )

        except Exception as e:

            log_program_event(
                "Login failed",
                details={
                    "client_id": cid,
                    "error": str(e)
                }
            )

    return sessions