# import threading
#
#
# _orders = []
# _lock = threading.Lock()
#
#
# def add_order(order):
#     order = order.copy()
#
#     with _lock:
#         app_order_id = order.get("app_order_id")
#
#         # Prevent duplicate order records
#         for existing in _orders:
#             if (
#                 app_order_id
#                 and str(existing.get("app_order_id"))
#                 == str(app_order_id)
#             ):
#                 existing.update(order)
#                 return existing.copy()
#
#         _orders.append(order)
#
#     return order
#
#
# def update_order(app_order_id, **updates):
#     with _lock:
#         for order in _orders:
#             if str(order.get("app_order_id")) == str(app_order_id):
#                 print(
#                     f"ORDER BOOK UPDATE: "
#                     f"{app_order_id} -> {updates.get('status')}"
#                 )
#                 order.update(updates)
#                 return order.copy()
#
#     print(
#         f"ORDER BOOK UPDATE FAILED: "
#         f"{app_order_id} not found"
#     )
#     return None
#
#
# def get_orders():
#     with _lock:
#         return [order.copy() for order in _orders]
#
#
# def get_order(app_order_id):
#     with _lock:
#         for order in _orders:
#             if (
#                 str(order.get("app_order_id"))
#                 == str(app_order_id)
#             ):
#                 return order.copy()
#
#     return None
#
#
# def get_client_orders(client_id):
#     with _lock:
#         return [
#             order.copy()
#             for order in _orders
#             if str(order.get("client_id")) == str(client_id)
#         ]
#
#
# def clear_orders():
#     global _orders
#
#     with _lock:
#         _orders = []

"""orderbook_manager.py"""
import threading


_orders = []
_pending_updates = {}

_lock = threading.Lock()


def add_order(order):
    order = order.copy()

    with _lock:
        app_order_id = order.get("app_order_id")

        if app_order_id:
            app_order_id = str(app_order_id)
            order["app_order_id"] = app_order_id

            # Apply socket update if it arrived before add_order()
            pending = _pending_updates.pop(app_order_id, None)

            if pending:
                order.update(pending)

        # Prevent duplicate order records
        for existing in _orders:
            if (
                app_order_id
                and str(existing.get("app_order_id"))
                == app_order_id
            ):
                existing.update(order)
                return existing.copy()

        _orders.append(order)

    return order


def update_order(app_order_id, **updates):

    app_order_id = str(app_order_id)

    with _lock:
        for order in _orders:
            if (
                str(order.get("app_order_id"))
                == app_order_id
            ):
                order.update(updates)

                print(
                    f"ORDER BOOK UPDATED: "
                    f"{app_order_id} -> "
                    f"{updates.get('status')}"
                )

                return order.copy()

        # Order hasn't been added yet.
        # Store socket update temporarily.
        _pending_updates[app_order_id] = updates

        print(
            f"ORDER NOT YET ADDED: "
            f"{app_order_id} | "
            f"storing update: {updates.get('status')}"
        )

    return None


def get_orders():
    with _lock:
        return [order.copy() for order in _orders]


def get_order(app_order_id):
    app_order_id = str(app_order_id)

    with _lock:
        for order in _orders:
            if (
                str(order.get("app_order_id"))
                == app_order_id
            ):
                return order.copy()

    return None


def get_client_orders(client_id):
    with _lock:
        return [
            order.copy()
            for order in _orders
            if str(order.get("client_id"))
            == str(client_id)
        ]


def clear_orders():
    global _orders
    global _pending_updates

    with _lock:
        _orders = []
        _pending_updates = {}