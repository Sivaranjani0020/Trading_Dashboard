"""
socket_listener.py

Trading Dashboard Interactive Socket.

Responsibilities:
- Maintain one Interactive Socket per logged-in client.
- Receive order status updates from AETRAM.
- Update Order Book.
- When an entry order is FILLED, create/update the position.
- When a panic square-off order is FILLED, close the position.
- Continuously update LTP and P&L for OPEN positions.
"""

import configparser
import json
import os
import socket
import threading
import time

import socketio

from helper_funct.client_market_details import fetch_ltp

from services.orderbook_manager import (
    update_order,
    get_order,
)

from services.position_manager import (
    add_position,
    update_position,
    get_position,
    get_open_positions,
)


# =============================================================
# ACTIVE SOCKET CLIENTS
# =============================================================

socket_clients = {}

_socket_lock = threading.Lock()


# =============================================================
# POSITION LTP MONITOR
# =============================================================

_position_monitor_thread = None
_position_monitor_stop = threading.Event()


def _segment_to_int(exchange_segment):
    """
    Convert exchange segment name/code to XTS numeric segment.
    """

    if exchange_segment is None:
        return None

    segment = str(exchange_segment).upper().strip()

    segment_map = {
        # NSE
        "NSECM": 1,
        "NSE": 1,
        "1": 1,

        "NSEFO": 2,
        "NFO": 2,
        "2": 2,

        # BSE
        "BSECM": 11,
        "BSE": 11,
        "11": 11,

        "BSEFO": 12,
        "BFO": 12,
        "12": 12,
    }

    return segment_map.get(segment)


def _position_ltp_loop():
    """
    Background thread.

    Continuously:
        OPEN position
            ↓
        Fetch latest LTP
            ↓
        Update position
            ↓
        Recalculate P&L
    """

    print("POSITION LTP MONITOR STARTED")

    while not _position_monitor_stop.is_set():

        try:

            positions = get_open_positions()

            # -------------------------------------------------
            # No open positions
            # -------------------------------------------------

            if not positions:

                _position_monitor_stop.wait(1)

                continue

            # -------------------------------------------------
            # Update every open position
            # -------------------------------------------------

            for position in positions:

                try:

                    client_id = str(
                        position.get("client_id")
                    )

                    app_order_id = str(
                        position.get("app_order_id")
                    )

                    instrument_id = position.get(
                        "instrument_id"
                    )

                    exchange_segment = position.get(
                        "exchange_segment"
                    )

                    # -----------------------------------------
                    # Validate instrument
                    # -----------------------------------------

                    if instrument_id in [
                        None,
                        "",
                        "None",
                    ]:
                        continue

                    segment = _segment_to_int(
                        exchange_segment
                    )

                    if segment is None:
                        print(
                            f"Invalid exchange segment "
                            f"for {client_id}: "
                            f"{exchange_segment}"
                        )
                        continue

                    # -----------------------------------------
                    # Get client's market socket/session
                    # -----------------------------------------

                    with _socket_lock:

                        socket_client = socket_clients.get(
                            client_id
                        )

                    if not socket_client:
                        continue

                    market_client = (
                        socket_client.market_client
                    )

                    if not market_client:
                        continue

                    # -----------------------------------------
                    # Fetch LTP
                    # -----------------------------------------

                    ltp = fetch_ltp(
                        market_client,
                        segment,
                        int(instrument_id)
                    )

                    if ltp is None:
                        continue

                    # -----------------------------------------
                    # Update LTP + P&L
                    # -----------------------------------------

                    updated = update_position_ltp(
                        client_id,
                        app_order_id,
                        ltp
                    )

                    if updated:

                        print(
                            f"LTP UPDATE | "
                            f"{client_id} | "
                            f"{position.get('symbol')} | "
                            f"LTP={ltp} | "
                            f"PnL={updated.get('pnl', 0)}"
                        )

                except Exception as e:

                    print(
                        f"Position LTP error "
                        f"[{position.get('client_id')}]: "
                        f"{e}"
                    )

        except Exception as e:

            print(
                f"Position monitor error: {e}"
            )

        # -----------------------------------------------------
        # Wait before next cycle
        # -----------------------------------------------------

        _position_monitor_stop.wait(1)


def update_position_ltp(
    client_id,
    app_order_id,
    ltp
):
    """
    Wrapper around position_manager.update_ltp().
    """

    from services.position_manager import update_ltp

    return update_ltp(
        client_id,
        app_order_id,
        ltp
    )


def start_position_ltp_monitor():
    """
    Start the background position LTP monitor.
    """

    global _position_monitor_thread

    # Already running
    if (
        _position_monitor_thread
        and _position_monitor_thread.is_alive()
    ):
        return

    _position_monitor_stop.clear()

    _position_monitor_thread = threading.Thread(
        target=_position_ltp_loop,
        daemon=True,
        name="Position-LTP-Monitor"
    )

    _position_monitor_thread.start()

    print(
        "Position LTP monitor thread started."
    )


def stop_position_ltp_monitor():
    """
    Stop the background position LTP monitor.
    """

    _position_monitor_stop.set()

    print(
        "Position LTP monitor stopped."
    )


# =============================================================
# PROCESS FILLED ORDER
# =============================================================

def process_filled_order(
    client_id,
    app_order_id
):
    """
    Process a FILLED order.

    Handles both:

        ENTRY ORDER
            ↓
        Create OPEN position

    and:

        EXIT ORDER
            ↓
        Close existing position
    """

    try:

        app_order_id = str(app_order_id)

        # -----------------------------------------------------
        # Get order from dashboard order book
        # -----------------------------------------------------

        dashboard_order = get_order(
            app_order_id
        )

        if dashboard_order is None:

            print(
                f"FILLED ORDER NOT FOUND "
                f"IN ORDER BOOK: {app_order_id}"
            )

            return False

        # -----------------------------------------------------
        # Make sure this order is actually Filled
        # -----------------------------------------------------

        status = str(
            dashboard_order.get(
                "status",
                ""
            )
        ).lower()

        if status != "filled":

            return False

        # -----------------------------------------------------
        # Common values
        # -----------------------------------------------------

        average_price = float(
            dashboard_order.get(
                "average_price"
            )
            or dashboard_order.get(
                "price"
            )
            or 0
        )

        order_side = str(
            dashboard_order.get(
                "order_side"
            )
            or dashboard_order.get(
                "side"
            )
            or ""
        ).upper()

        quantity = int(
            dashboard_order.get(
                "filled_quantity"
            )
            or dashboard_order.get(
                "quantity"
            )
            or dashboard_order.get(
                "qty"
            )
            or 0
        )

        symbol = (
            dashboard_order.get("symbol")
            or ""
        )

        # =====================================================
        # EXIT ORDER
        # =====================================================

        is_exit = bool(
            dashboard_order.get(
                "is_exit",
                False
            )
        )

        position_id = dashboard_order.get(
            "position_id"
        )

        if is_exit and position_id:

            position_id = str(position_id)

            print(
                f">>> EXIT ORDER FILLED <<< "
                f"{client_id} / "
                f"{position_id}"
            )

            # -------------------------------------------------
            # Get original position
            # -------------------------------------------------

            position = get_position(
                client_id,
                position_id
            )

            if position is None:

                print(
                    f"Original position not found "
                    f"for exit order: {position_id}"
                )

                return False

            # -------------------------------------------------
            # Calculate final P&L
            # -------------------------------------------------

            entry_price = float(
                position.get(
                    "entry_price"
                )
                or 0
            )

            quantity = int(
                position.get("quantity")
                or position.get("qty")
                or quantity
                or 0
            )

            original_side = str(
                position.get("side", "")
            ).upper()

            exit_price = average_price

            if original_side == "BUY":

                final_pnl = (
                    (exit_price - entry_price)
                    * quantity
                )

            else:

                final_pnl = (
                    (entry_price - exit_price)
                    * quantity
                )

            # -------------------------------------------------
            # Close position
            # -------------------------------------------------

            updated = update_position(
                client_id,
                position_id,
                status="CLOSED",
                quantity=0,
                exit_price=exit_price,
                ltp=exit_price,
                pnl=round(final_pnl, 2)
            )

            print(
                f"POSITION CLOSED | "
                f"{client_id} | "
                f"{position_id} | "
                f"Exit={exit_price} | "
                f"Final P&L={round(final_pnl, 2)}"
            )

            return updated is not None

        # =====================================================
        # ENTRY ORDER
        # =====================================================

        print(
            f">>> ENTRY ORDER FILLED <<< "
            f"{client_id} / {app_order_id}"
        )

        # -----------------------------------------------------
        # Check if position already exists
        # -----------------------------------------------------

        existing_position = get_position(
            client_id,
            app_order_id
        )

        if existing_position:

            updated = update_position(
                client_id,
                app_order_id,
                status="OPEN",
                entry_price=average_price,
                ltp=average_price,
                pnl=0
            )

            print(
                f"Position already existed. "
                f"Updated to OPEN: "
                f"{client_id} / {app_order_id}"
            )

            return updated is not None

        # -----------------------------------------------------
        # Create new OPEN position
        # -----------------------------------------------------

        position_data = {
            "position_id": app_order_id,

            "client_id": client_id,

            "app_order_id": app_order_id,

            "instrument_id":
                dashboard_order.get(
                    "instrument_id"
                ),

            "symbol": symbol,

            "side": order_side,

            "quantity": quantity,

            # Keep both for compatibility
            "qty": quantity,

            "entry_price": average_price,

            "ltp": average_price,

            "pnl": 0,

            "status": "OPEN",

            "product":
                dashboard_order.get(
                    "product"
                )
                or dashboard_order.get(
                    "product_type"
                )
                or "NRML",

            "exchange_segment":
                dashboard_order.get(
                    "exchange_segment"
                ),
        }

        add_position(
            position_data
        )

        print(
            f">>> POSITION OPENED <<< "
            f"{client_id} / {symbol} | "
            f"Qty={quantity} | "
            f"Entry={average_price}"
        )

        return True

    except Exception as e:

        print(
            f"Process filled order error "
            f"[{client_id} / {app_order_id}]: "
            f"{e}"
        )

        return False


# =============================================================
# ORDER SOCKET
# =============================================================

class OrderSocketIO:

    def __init__(
        self,
        client_id,
        token,
        user_id,
        api_client,
        market_client,
    ):

        self.client_id = client_id
        self.token = token
        self.user_id = user_id
        self.api_client = api_client
        self.market_client = market_client

        self.sid = socketio.Client(
            logger=True,
            engineio_logger=True,
            reconnection=True,
            reconnection_attempts=0,
        )

        self.eventlistener = self.sid

        # -----------------------------------------------------
        # Register events
        # -----------------------------------------------------

        self.sid.on(
            "connect",
            self.on_connect
        )

        self.sid.on(
            "message",
            self.on_message
        )

        self.sid.on(
            "joined",
            self.on_joined
        )

        self.sid.on(
            "error",
            self.on_error
        )

        self.sid.on(
            "order",
            self.on_order
        )

        self.sid.on(
            "trade",
            self.on_trade
        )

        self.sid.on(
            "position",
            self.on_position
        )

        self.sid.on(
            "tradeConversion",
            self.on_tradeconversion
        )

        self.sid.on(
            "logout",
            self.on_logout
        )

        self.sid.on(
            "disconnect",
            self.on_disconnect
        )

        self.sid.on(
            "socketError",
            self.on_socket_error
        )

        # -----------------------------------------------------
        # Read socket root URL
        # -----------------------------------------------------

        current_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        config_path = os.path.join(
            current_dir,
            "config.ini"
        )

        config = configparser.RawConfigParser()

        config.read(
            config_path
        )

        try:

            root_url = config.get(
                "root_url",
                "root"
            ).strip()

        except Exception:

            root_url = (
                "https://secure.aetramtrades.in"
            )

        self.connection_url = (
            f"{root_url}/"
            f"?token={self.token}"
            f"&userID={self.user_id}"
            f"&apiType=INTERACTIVE"
        )

    # =========================================================
    # CONNECT
    # =========================================================

    def connect(self):

        print("\n================================")
        print(
            f"Connecting socket for client: "
            f"{self.client_id}"
        )
        print("================================")

        try:

            host = (
                "secure.aetramtrades.in"
            )

            port = 443

            # -------------------------------------------------
            # DNS / TCP test
            # -------------------------------------------------

            try:

                ip = socket.gethostbyname(
                    host
                )

                print(
                    f"DNS OK: {host} -> {ip}"
                )

                s = socket.create_connection(
                    (host, port),
                    timeout=10
                )

                print(
                    "TCP connection successful"
                )

                s.close()

            except Exception as e:

                print(
                    "TCP test failed:",
                    repr(e)
                )

            # -------------------------------------------------
            # Socket.IO connection
            # -------------------------------------------------

            self.sid.connect(
                url=self.connection_url,
                headers={},
                transports=["websocket"],
                socketio_path="/interactive/socket.io",
            )

            print(
                f"Socket connected successfully: "
                f"{self.client_id}"
            )

            self.sid.wait()

        except Exception as e:

            print(
                f"Socket connection failed "
                f"for {self.client_id}: {e}"
            )

    # =========================================================
    # ORDER EVENT
    # =========================================================

    def on_order(self, data):

        try:

            print("\n==============================")
            print(
                f"ORDER EVENT - "
                f"{self.client_id}"
            )
            print(data)
            print("==============================")

            # -------------------------------------------------
            # Parse AETRAM response
            # -------------------------------------------------

            if isinstance(data, str):

                order = json.loads(data)

            else:

                order = data

            app_order_id = order.get(
                "AppOrderID"
            )

            status = order.get(
                "OrderStatus"
            )

            order_side = (
                order.get("OrderSide")
                or order.get("OrderSideType")
                or ""
            )

            quantity = (
                order.get("OrderQuantity")
                or order.get("OrderQuantityAPI")
                or 0
            )

            average_price = (
                order.get(
                    "OrderAverageTradedPriceAPI"
                )
                or order.get(
                    "AverageTradedPrice"
                )
                or order.get(
                    "OrderAverageTradedPrice"
                )
                or 0
            )

            symbol = (
                order.get("TradingSymbol")
                or order.get(
                    "TradingSymbolName"
                )
                or order.get("Symbol")
                or ""
            )

            print(
                "CLIENT       :",
                self.client_id
            )

            print(
                "APP ORDER ID :",
                app_order_id
            )

            print(
                "STATUS       :",
                status
            )

            print(
                "SIDE         :",
                order_side
            )

            print(
                "SYMBOL       :",
                symbol
            )

            print(
                "QTY          :",
                quantity
            )

            print(
                "AVG PRICE    :",
                average_price
            )

            # -------------------------------------------------
            # Validate AppOrderID
            # -------------------------------------------------

            if not app_order_id:

                print(
                    "No AppOrderID received."
                )

                return

            app_order_id = str(
                app_order_id
            )

            # -------------------------------------------------
            # Update Order Book
            #
            # If order hasn't been added yet,
            # orderbook_manager stores the update
            # in pending_updates.
            # -------------------------------------------------

            update_order(
                app_order_id,

                status=status,

                filled_quantity=quantity,

                average_price=average_price,

                order_side=order_side,

                symbol=symbol,
            )

            # -------------------------------------------------
            # Only process Filled
            # -------------------------------------------------

            if (
                str(status).lower()
                != "filled"
            ):

                return

            print(
                f">>> FILLED EVENT RECEIVED "
                f"FOR {self.client_id} <<<"
            )

            # -------------------------------------------------
            # Process Filled order
            #
            # This handles:
            # ENTRY -> OPEN position
            # EXIT  -> CLOSED position
            # -------------------------------------------------

            process_filled_order(
                self.client_id,
                app_order_id
            )

        except Exception as e:

            print(
                f"Socket Order Error "
                f"[{self.client_id}]: {e}"
            )

    # =========================================================
    # OTHER EVENTS
    # =========================================================

    def on_connect(self):

        print("\n================================")

        print(
            f"INTERACTIVE SOCKET CONNECTED: "
            f"{self.client_id}"
        )

        print(
            "SID:",
            self.sid.sid
        )

        print(
            "ENGINEIO SID:",
            self.sid.eio.sid
        )

        print("================================")

    def on_message(self, data=None):

        print(
            f"Socket message "
            f"[{self.client_id}]:",
            data
        )

    def on_joined(self, data):

        print(
            f"Interactive socket joined: "
            f"{self.client_id}"
        )

        print(data)

    def on_error(self, data):

        print(
            f"Interactive socket error "
            f"[{self.client_id}]:",
            data
        )

    def on_socket_error(self, data):

        print(
            f"AETRAM SOCKET ERROR "
            f"[{self.client_id}]:"
        )

        print(data)

    def on_trade(self, data):

        print(
            f"TRADE EVENT "
            f"[{self.client_id}]"
        )

        print(data)

    def on_position(self, data):

        print(
            f"POSITION EVENT "
            f"[{self.client_id}]"
        )

        print(data)

    def on_tradeconversion(self, data):

        print(
            f"TRADE CONVERSION EVENT "
            f"[{self.client_id}]"
        )

        print(data)

    def on_logout(self, data):

        print(
            f"USER LOGGED OUT: "
            f"{self.client_id}"
        )

        print(data)

    def on_disconnect(self):

        print("\n================================")

        print(
            f"INTERACTIVE SOCKET DISCONNECTED: "
            f"{self.client_id}"
        )

        print(
            "Socket connected state:",
            self.sid.connected
        )

        print("================================")

    def get_emitter(self):

        return self.eventlistener


# =============================================================
# START ONE CLIENT SOCKET
# =============================================================

def start_socket(
    client_id,
    client_session
):

    global socket_clients

    with _socket_lock:

        # -----------------------------------------------------
        # Check existing socket
        # -----------------------------------------------------

        if client_id in socket_clients:

            existing = socket_clients[
                client_id
            ]

            if existing.sid.connected:

                print(
                    f"Socket already running "
                    f"for {client_id}"
                )

                return existing

        # -----------------------------------------------------
        # Get sessions
        # -----------------------------------------------------

        interactive_xt = client_session[
            "Interactive_Xt"
        ]

        market_xt = client_session[
            "Market_Xt"
        ]

        # -----------------------------------------------------
        # Create socket client
        # -----------------------------------------------------

        socket_client = OrderSocketIO(

            client_id=client_id,

            token=interactive_xt.token,

            user_id=interactive_xt.userID,

            api_client=interactive_xt,

            market_client=market_xt,
        )

        socket_clients[
            client_id
        ] = socket_client

        # -----------------------------------------------------
        # Start socket thread
        # -----------------------------------------------------

        threading.Thread(

            target=socket_client.connect,

            daemon=True,

            name=f"Socket-{client_id}"

        ).start()

        print(
            f"Socket thread started "
            f"for {client_id}"
        )

        return socket_client


# =============================================================
# START ALL CLIENT SOCKETS
# =============================================================

def start_sockets(
    client_sessions
):

    for client_id, client_session in (
        client_sessions.items()
    ):

        try:

            start_socket(
                client_id,
                client_session
            )

        except Exception as e:

            print(
                f"Failed to start socket "
                f"for {client_id}: {e}"
            )

    # ---------------------------------------------------------
    # Start LTP monitor
    # ---------------------------------------------------------

    start_position_ltp_monitor()


# =============================================================
# STOP SOCKETS
# =============================================================

def stop_sockets():

    global socket_clients

    # ---------------------------------------------------------
    # Stop LTP monitor first
    # ---------------------------------------------------------

    stop_position_ltp_monitor()

    with _socket_lock:

        for client_id, client in (
            list(socket_clients.items())
        ):

            try:

                if client.sid.connected:

                    client.sid.disconnect()

                    print(
                        f"Socket disconnected: "
                        f"{client_id}"
                    )

            except Exception as e:

                print(
                    f"Socket disconnect error "
                    f"[{client_id}]: {e}"
                )

        socket_clients.clear()