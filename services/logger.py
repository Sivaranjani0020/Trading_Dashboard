"""
logger.py
Centralized SQLite logging system.
"""

from datetime import datetime
from database import insert_program_log, insert_order_log


def log_program_event(event: str, details: dict = None):
    """
    Log program-level events.
    """
    try:
        insert_program_log(
            datetime.now().isoformat(),
            event,
            details or {}
        )

        print(f"[PROGRAM LOG] {event} | {details}")

    except Exception as e:
        print(f"[ERROR] Failed to log program event: {event} | {e}")


def log_order_event(
    client_id: str,
    action: str,
    parsed_call: dict,
    response: dict
):
    """
    Log runtime order events.
    """
    try:
        insert_order_log(
            timestamp=datetime.now().isoformat(),
            client_id=client_id,
            action=action,
            symbol=parsed_call.get("symbol"),
            token=parsed_call.get("token"),
            side=parsed_call.get("side"),
            qty=parsed_call.get("qty"),
            sl=parsed_call.get("sl"),
            target=parsed_call.get("target"),
            response=response
        )

        print(
            f"[ORDER LOG] {client_id} | {action} | "
            f"{parsed_call.get('symbol')} | {response}"
        )

    except Exception as e:
        print(
            f"[ERROR] Failed to log order event "
            f"for {client_id}: {action} | {e}"
        )