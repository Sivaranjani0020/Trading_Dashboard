# """position_manager.py"""
# import threading
#
#
# _positions = []
# _lock = threading.Lock()
#
#
# def add_position(position):
#     """
#     Add a new position/order record.
#
#     Expected fields:
#         client_id
#         app_order_id
#         instrument_id
#         symbol
#         side
#         qty
#         entry_price
#         ltp
#         pnl
#         status
#         product
#     """
#
#     position = position.copy()
#
#     position.setdefault("status", "PendingNew")
#     position.setdefault("ltp", position.get("entry_price", 0))
#     position.setdefault("pnl", 0)
#     position.setdefault("product", "NRML")
#
#     with _lock:
#         # Prevent duplicate position records
#         for existing in _positions:
#             if (
#                 str(existing.get("client_id")) == str(position.get("client_id"))
#                 and str(existing.get("app_order_id"))
#                 == str(position.get("app_order_id"))
#             ):
#                 return existing
#
#         _positions.append(position)
#
#     return position
#
#
# def get_positions():
#     with _lock:
#         return [position.copy() for position in _positions]
#
#
# def get_position(client_id, app_order_id):
#     with _lock:
#         for position in _positions:
#             if (
#                 str(position.get("client_id")) == str(client_id)
#                 and str(position.get("app_order_id"))
#                 == str(app_order_id)
#             ):
#                 return position.copy()
#
#     return None
#
#
# def update_position(client_id, app_order_id, **updates):
#     with _lock:
#         for position in _positions:
#             if (
#                 str(position.get("client_id")) == str(client_id)
#                 and str(position.get("app_order_id"))
#                 == str(app_order_id)
#             ):
#                 position.update(updates)
#                 return position.copy()
#
#     return None
#
#
# def update_status(client_id, app_order_id, status):
#     return update_position(
#         client_id,
#         app_order_id,
#         status=status
#     )
#
#
# def update_ltp(client_id, app_order_id, ltp):
#     position = get_position(client_id, app_order_id)
#
#     if not position:
#         return None
#
#     entry_price = float(position.get("entry_price") or 0)
#     qty = int(position.get("qty") or 0)
#     side = str(position.get("side", "")).upper()
#
#     ltp = float(ltp)
#
#     if side == "BUY":
#         pnl = (ltp - entry_price) * qty
#     else:
#         pnl = (entry_price - ltp) * qty
#
#     return update_position(
#         client_id,
#         app_order_id,
#         ltp=ltp,
#         pnl=round(pnl, 2)
#     )
#
#
# def close_position(client_id, app_order_id, exit_price=None):
#     updates = {
#         "status": "CLOSED"
#     }
#
#     if exit_price is not None:
#         updates["exit_price"] = float(exit_price)
#
#     return update_position(
#         client_id,
#         app_order_id,
#         **updates
#     )
#
#
# def get_open_positions():
#     with _lock:
#         return [
#             position.copy()
#             for position in _positions
#             if str(position.get("status", "")).upper() == "OPEN"
#         ]
#
#
# def get_selected_positions(selected_orders):
#     """
#     selected_orders example:
#
#     [
#         {
#             "client_id": "CLIENT001",
#             "app_order_id": "12345"
#         }
#     ]
#     """
#
#     selected = []
#
#     with _lock:
#         for item in selected_orders:
#             client_id = item.get("client_id")
#             app_order_id = item.get("app_order_id")
#
#             for position in _positions:
#                 if (
#                     str(position.get("client_id")) == str(client_id)
#                     and str(position.get("app_order_id"))
#                     == str(app_order_id)
#                 ):
#                     selected.append(position.copy())
#
#     return selected
#
#
# def remove_position(client_id, app_order_id):
#     global _positions
#
#     with _lock:
#         _positions = [
#             position
#             for position in _positions
#             if not (
#                 str(position.get("client_id")) == str(client_id)
#                 and str(position.get("app_order_id"))
#                 == str(app_order_id)
#             )
#         ]
#
#
# def clear_positions():
#     global _positions
#
#     with _lock:
#         _positions = []

"""position_manager.py"""

import threading


_positions = []
_lock = threading.Lock()


def add_position(position):
    """
    Add a new position record.

    Expected fields:
        client_id
        app_order_id
        position_id
        instrument_id
        symbol
        side
        quantity / qty
        entry_price
        ltp
        pnl
        status
        product
        exchange_segment
    """

    position = position.copy()

    # ---------------------------------------------------------
    # Normalize quantity fields
    # ---------------------------------------------------------
    if "quantity" not in position and "qty" in position:
        position["quantity"] = position["qty"]

    if "qty" not in position and "quantity" in position:
        position["qty"] = position["quantity"]

    # ---------------------------------------------------------
    # Default values
    # ---------------------------------------------------------
    position.setdefault("status", "PendingNew")
    position.setdefault("entry_price", 0)
    position.setdefault("ltp", position.get("entry_price", 0))
    position.setdefault("pnl", 0)
    position.setdefault("product", "NRML")

    # Position ID should normally be the original AppOrderID
    if "position_id" not in position:
        position["position_id"] = position.get("app_order_id")

    with _lock:

        # -----------------------------------------------------
        # Prevent duplicate position records
        # -----------------------------------------------------
        for existing in _positions:
            if (
                str(existing.get("client_id"))
                == str(position.get("client_id"))
                and
                str(existing.get("app_order_id"))
                == str(position.get("app_order_id"))
            ):
                # Update existing record with latest information
                existing.update(position)
                return existing.copy()

        # -----------------------------------------------------
        # Add new position
        # -----------------------------------------------------
        _positions.append(position)

    return position.copy()


def get_positions():
    """Return all positions."""

    with _lock:
        return [position.copy() for position in _positions]


def get_position(client_id, app_order_id):
    """Get one position using client ID + AppOrderID."""

    with _lock:
        for position in _positions:

            if (
                str(position.get("client_id"))
                == str(client_id)
                and
                str(position.get("app_order_id"))
                == str(app_order_id)
            ):
                return position.copy()

    return None


def update_position(client_id, app_order_id, **updates):
    """Update an existing position."""

    with _lock:

        for position in _positions:

            if (
                str(position.get("client_id"))
                == str(client_id)
                and
                str(position.get("app_order_id"))
                == str(app_order_id)
            ):

                position.update(updates)

                # Keep quantity fields synchronized
                if "quantity" in updates:
                    position["qty"] = updates["quantity"]

                elif "qty" in updates:
                    position["quantity"] = updates["qty"]

                return position.copy()

    return None


def update_status(client_id, app_order_id, status):
    """Update position status."""

    return update_position(
        client_id,
        app_order_id,
        status=status
    )


def update_ltp(client_id, app_order_id, ltp):
    """
    Update LTP and calculate P&L.

    BUY:
        P&L = (LTP - Entry Price) × Quantity

    SELL:
        P&L = (Entry Price - LTP) × Quantity
    """

    position = get_position(
        client_id,
        app_order_id
    )

    if not position:
        return None

    if str(
            position.get("status", "")
    ).upper() == "CLOSED":
        return position
    try:
        entry_price = float(
            position.get("entry_price") or 0
        )

        # -----------------------------------------------------
        # IMPORTANT:
        # Support both quantity and qty
        # -----------------------------------------------------
        qty = int(
            position.get("quantity")
            or position.get("qty")
            or 0
        )

        side = str(
            position.get("side", "")
        ).upper()

        ltp = float(ltp)

        # -----------------------------------------------------
        # Calculate P&L
        # -----------------------------------------------------
        if side == "BUY":

            pnl = (
                (ltp - entry_price)
                * qty
            )

        elif side == "SELL":

            pnl = (
                (entry_price - ltp)
                * qty
            )

        else:
            pnl = 0

        # -----------------------------------------------------
        # Update position
        # -----------------------------------------------------
        return update_position(
            client_id,
            app_order_id,
            ltp=ltp,
            pnl=round(pnl, 2)
        )

    except Exception as e:

        print(
            f"Position LTP update error "
            f"[{client_id} / {app_order_id}]: {e}"
        )

        return None


def close_position(
    client_id,
    app_order_id,
    exit_price=None
):
    """Close a position."""

    updates = {
        "status": "CLOSED"
    }

    if exit_price is not None:

        updates["exit_price"] = float(
            exit_price
        )

        updates["ltp"] = float(
            exit_price
        )

    return update_position(
        client_id,
        app_order_id,
        **updates
    )


def get_open_positions():
    """Return only OPEN positions."""

    with _lock:

        return [
            position.copy()
            for position in _positions
            if str(
                position.get("status", "")
            ).upper() == "OPEN"
        ]


def get_selected_positions(selected_orders):
    """
    Get selected positions.

    Expected input:

    [
        {
            "client_id": "CLIENT001",
            "app_order_id": "12345"
        }
    ]
    """

    selected = []

    with _lock:

        for item in selected_orders:

            client_id = item.get(
                "client_id"
            )

            app_order_id = item.get(
                "app_order_id"
            )

            for position in _positions:

                if (
                    str(position.get("client_id"))
                    == str(client_id)
                    and
                    str(position.get("app_order_id"))
                    == str(app_order_id)
                ):

                    selected.append(
                        position.copy()
                    )

    return selected


def remove_position(
    client_id,
    app_order_id
):
    """Remove one position."""

    global _positions

    with _lock:

        _positions = [
            position
            for position in _positions

            if not (
                str(position.get("client_id"))
                == str(client_id)

                and

                str(position.get("app_order_id"))
                == str(app_order_id)
            )
        ]


def clear_positions():
    """Remove all positions."""

    global _positions

    with _lock:
        _positions = []