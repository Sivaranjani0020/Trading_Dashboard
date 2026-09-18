

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session
)
from functools import wraps
from datetime import datetime
import os

from helper_funct.client_login import login_xts

from helper_funct.client_order_funct import (
    place_market_order,
    place_limit_order,
)

from helper_funct.client_market_details import fetch_ltp

from services.client_manager import load_enabled_clients
from database import (
    get_admin,
    get_all_client_credentials,
    get_all_enabled_client_rows,
    get_enabled_client,
    set_client_enabled,
    set_client_lots,
    add_client,
    delete_client,
    update_client_credentials,
    delete_admin,
    add_admin,
    update_admin_password,
    get_all_admins,
    get_client_credentials
)
from services.instrument_manager import (
    initialize_master,
    get_symbols,
    get_expiries,
    get_strikes,
    get_option_contract,
    get_equity_contract,
)

from services.orderbook_manager import (
    add_order,
    get_orders,
)

from services.position_manager import (
    get_positions,
)

from services.socket_listener import (
    start_sockets,
    stop_sockets,
    process_filled_order,
)


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "trading-dashboard-secret"
)



# XTS sessions are kept in memory.
# Key = client_id
app.config["CLIENT_SESSIONS"] = {}


# ============================================================
# ADMIN AUTH
# ============================================================

def admin_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        if not session.get(
            "admin_logged_in"
        ):
            return redirect(
                url_for("admin_login")
            )

        return f(*args, **kwargs)

    return decorated


@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        userid = request.form.get(
            "userid"
        )

        password = request.form.get(
            "password"
        )

        admin = get_admin(userid)

        if admin:

            if str(admin["password"]) == str(password):
                session[
                    "admin_logged_in"
                ] = True

                session[
                    "admin_userid"
                ] = userid

                return redirect(
                    url_for("index")
                )

        return render_template(
            "admin_login.html",
            error="Invalid userid or password"
        )

    return render_template(
        "admin_login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    try:

        stop_sockets()

    except Exception as e:

        print(
            "Socket stop error:",
            e
        )

    app.config[
        "CLIENT_SESSIONS"
    ] = {}

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# ============================================================
# CLIENT LIST
# ============================================================

@app.route("/")
@admin_required
def index():

    try:

        credentials = get_all_client_credentials()
        enabled = get_all_enabled_client_rows()
        enabled_map = {}

        for row in enabled or []:

            enabled_map[
                str(row["client_id"])
            ] = row

        clients = []

        for row in credentials or []:

            client_id = str(
                row["client_id"]
            )

            enabled_row = (
                enabled_map.get(
                    client_id,
                    {}
                )
            )

            clients.append({

                "client_id":
                    client_id,

                "enabled":
                    bool(
                        enabled_row.get(
                            "enabled_flag",
                            False
                        )
                    ),

                "lots":
                    int(
                        enabled_row.get(
                            "lots",
                            1
                        ) or 1
                    )
            })

        enabled_set = {

            str(row["client_id"])

            for row in enabled or []

            if row.get(
                "enabled_flag"
            )
        }

        admins = get_all_admins()

        return render_template(
            "index.html",
            clients=clients,
            enabled_set=enabled_set,
            admins=admins
        )

    except Exception as e:

        print(
            "Client list error:",
            e
        )

        return render_template(
            "index.html",
            clients=[],
            enabled_set=set(),
            admins=[],
            error=str(e)
        )

# ============================================================
# ENABLE / DISABLE CLIENT
# ============================================================

@app.route(
    "/toggle_client",
    methods=["POST"]
)
@admin_required
def toggle_client():

    client_id = str(
        request.form.get(
            "client_id"
        )
    )

    enabled = (
        request.form.get(
            "enabled"
        ) == "true"
    )

    try:

        set_client_enabled(
            client_id,
            enabled
        )

        return jsonify({
            "success": True
        })

    except Exception as e:

        print(
            "Toggle client error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# UPDATE LOTS
# ============================================================

@app.route(
    "/update_lots",
    methods=["POST"]
)
@admin_required
def update_lots():

    client_id = str(
        request.form.get(
            "client_id"
        )
    )

    try:

        lots = int(
            request.form.get(
                "lots",
                1
            )
        )

    except (
        TypeError,
        ValueError
    ):

        lots = 1

    if lots < 1:
        lots = 1

    try:

        set_client_lots(
            client_id,
            lots
        )

        return jsonify({
            "success": True
        })

    except Exception as e:

        print(
            "Update lots error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
# ============================================================
# CLIENT MANAGEMENT
# ============================================================

@app.route("/add-client", methods=["POST"])
@admin_required
def add_client_route():

    data = request.form

    try:
        add_client(
            client_id=data["client_id"].strip(),
            interactive_api_key=data["interactive_api_key"].strip(),
            interactive_api_secret=data["interactive_api_secret"].strip(),
            market_api_key=data["market_api_key"].strip(),
            market_api_secret=data["market_api_secret"].strip(),
            static_ip_username=data.get(
                "static_ip_username", ""
            ).strip(),
            static_ip_password=data.get(
                "static_ip_password", ""
            ).strip(),
            static_ip_host=data.get(
                "static_ip_host", ""
            ).strip(),
            static_ip_port=(
                int(data["static_ip_port"])
                if data.get("static_ip_port")
                else None
            ),
            lots=int(data.get("lots", 1))
        )

        return redirect(url_for("index"))

    except Exception as e:

        print("Add client error:", e)

        return f"Error adding client: {e}", 400


@app.route("/delete-client", methods=["POST"])
@admin_required
def delete_client_route():

    client_id = request.form.get("client_id")

    try:
        delete_client(client_id)

        return redirect(url_for("index"))

    except Exception as e:

        print("Delete client error:", e)

        return f"Error deleting client: {e}", 400

# ============================================================
# UPDATE CLIENT CREDENTIALS
# ============================================================

@app.route("/update-client", methods=["POST"])
@admin_required
def update_client_route():

    data = request.form

    client_id = data.get("client_id", "").strip()

    try:

        update_client_credentials(
            client_id=client_id,

            interactive_api_key=
                data.get(
                    "interactive_api_key",
                    ""
                ).strip(),

            interactive_api_secret=
                data.get(
                    "interactive_api_secret",
                    ""
                ).strip(),

            market_api_key=
                data.get(
                    "market_api_key",
                    ""
                ).strip(),

            market_api_secret=
                data.get(
                    "market_api_secret",
                    ""
                ).strip(),

            static_ip_username=
                data.get(
                    "static_ip_username",
                    ""
                ).strip(),

            static_ip_password=
                data.get(
                    "static_ip_password",
                    ""
                ).strip(),

            static_ip_host=
                data.get(
                    "static_ip_host",
                    ""
                ).strip(),

            static_ip_port=(
                int(data["static_ip_port"])
                if data.get("static_ip_port")
                else None
            )
        )

        return redirect(url_for("index"))

    except Exception as e:

        print(
            "Update client error:",
            e
        )

        return (
            f"Error updating client: {e}",
            400
        )

# ============================================================
# ADMIN MANAGEMENT
# ============================================================
# ============================================================
# ADMIN MANAGEMENT
# ============================================================

@app.route("/add-admin", methods=["POST"])
@admin_required
def add_admin_route():

    userid = request.form.get("userid", "").strip()
    password = request.form.get("password", "")

    try:
        add_admin(userid, password)

        return redirect(url_for("index"))

    except Exception as e:

        print("Add admin error:", e)

        return f"Error adding admin: {e}", 400

@app.route("/update-admin", methods=["POST"])
@admin_required
def update_admin_route():

    userid = request.form.get(
        "userid",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    try:

        update_admin_password(
            userid,
            password
        )

        return redirect(
            url_for("index")
        )

    except Exception as e:

        print(
            "Update admin error:",
            e
        )

        return (
            f"Error updating admin: {e}",
            400
        )
@app.route("/delete-admin", methods=["POST"])
@admin_required
def delete_admin_route():

    userid = request.form.get("userid")

    try:
        delete_admin(userid)

        return redirect(url_for("index"))

    except Exception as e:

        print("Delete admin error:", e)

        return f"Error deleting admin: {e}", 400

# ============================================================
# GET CLIENT CREDENTIALS
# ============================================================

@app.route("/api/client-credentials")
@admin_required
def api_client_credentials():

    client_id = request.args.get(
        "client_id",
        ""
    ).strip()

    if not client_id:
        return jsonify({
            "success": False,
            "error": "Client ID is required"
        }), 400

    try:

        credentials = get_client_credentials(client_id)

        if not credentials:
            return jsonify({
                "success": False,
                "error": "Client not found"
            }), 404

        return jsonify({
            "success": True,
            "credentials": {
                "client_id": credentials["client_id"],
                "interactive_api_key": credentials["interactive_api_key"] or "",
                "interactive_api_secret": credentials["interactive_api_secret"] or "",
                "market_api_key": credentials["market_api_key"] or "",
                "market_api_secret": credentials["market_api_secret"] or "",
                "static_ip_username": credentials["static_ip_username"] or "",
                "static_ip_password": credentials["static_ip_password"] or "",
                "static_ip_host": credentials["static_ip_host"] or "",
                "static_ip_port": credentials["static_ip_port"] or ""
            }
        })

    except Exception as e:

        print(
            "Get client credentials error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
# ============================================================
# LOGIN ENABLED CLIENTS
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
@admin_required
def login_clients_route():

    try:

        enabled_clients = (
            load_enabled_clients()
        )

        if not enabled_clients:

            return jsonify({
                "success": False,
                "error": "No enabled clients"
            }), 400

        client_sessions = {}

        for client in enabled_clients:

            client_id = str(
                client["client_id"]
            )

            lots = int(
                client.get(
                    "lots",
                    1
                ) or 1
            )

            print(
                f"Logging in client: "
                f"{client_id}"
            )

            client_session = login_xts(
                client_id
            )

            if not client_session:

                print(
                    f"Login failed: "
                    f"{client_id}"
                )

                continue

            client_session[
                "lots"
            ] = lots

            client_sessions[
                client_id
            ] = client_session

        if not client_sessions:

            return jsonify({
                "success": False,
                "error": (
                    "No client login successful"
                )
            }), 400

        # ----------------------------------------------------
        # Store client sessions
        # ----------------------------------------------------

        app.config[
            "CLIENT_SESSIONS"
        ] = client_sessions

        # ----------------------------------------------------
        # Initialize master
        # ----------------------------------------------------

        first_session = next(
            iter(
                client_sessions.values()
            )
        )

        initialize_master(
            first_session[
                "Market_Xt"
            ]
        )

        # ----------------------------------------------------
        # Start sockets
        # ----------------------------------------------------

        start_sockets(
            client_sessions
        )

        session[
            "logged_clients"
        ] = list(
            client_sessions.keys()
        )

        return redirect(
            url_for("dashboard")
        )

    except Exception as e:

        print(
            "Client login error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@admin_required
def dashboard():

    return render_template(
        "dashboard.html"
    )


# ============================================================
# SYMBOL SEARCH
# ============================================================

@app.route("/api/symbols")
@admin_required
def api_symbols():

    instrument_type = request.args.get(
        "instrument_type",
        "OPTIONS"
    )

    search = request.args.get(
        "search",
        ""
    )

    print(
        "SYMBOL API CALLED:",
        instrument_type,
        repr(search)
    )

    try:

        symbols = get_symbols(
            instrument_type=instrument_type,
            search=search
        )

        print(
            "SYMBOLS RETURNED:",
            len(symbols),
            symbols[:20]
        )

        return jsonify({
            "success": True,
            "symbols": symbols
        })

    except Exception as e:

        print(
            "SYMBOL SEARCH ERROR:",
            repr(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# EXPIRIES
# ============================================================

@app.route("/api/expiries")
@admin_required
def api_expiries():

    symbol = request.args.get(
        "symbol",
        ""
    ).strip()

    try:

        expiries = get_expiries(
            symbol
        )

        return jsonify({
            "success": True,
            "expiries": expiries
        })

    except Exception as e:

        print(
            "Expiry error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# STRIKES
# ============================================================

@app.route("/api/strikes")
@admin_required
def api_strikes():

    symbol = request.args.get(
        "symbol",
        ""
    ).strip()

    expiry = request.args.get(
        "expiry",
        ""
    ).strip()

    try:

        strikes = get_strikes(
            symbol,
            expiry
        )

        return jsonify({
            "success": True,
            "strikes": strikes
        })

    except Exception as e:

        print(
            "Strike error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# CONTRACT
# ============================================================

@app.route("/api/contract")
@admin_required
def api_contract():

    symbol = request.args.get(
        "symbol",
        ""
    ).strip()

    instrument_type = request.args.get(
        "instrument_type",
        "OPTIONS"
    ).upper()

    if not symbol:

        return jsonify({
            "success": False,
            "error": "Symbol is required"
        }), 400

    try:

        # ----------------------------------------------------
        # EQUITY
        # ----------------------------------------------------

        if instrument_type == "EQUITY":

            contract = get_equity_contract(
                symbol
            )

        # ----------------------------------------------------
        # OPTIONS
        # ----------------------------------------------------

        else:

            expiry = request.args.get(
                "expiry",
                ""
            ).strip()

            strike = request.args.get(
                "strike",
                ""
            ).strip()

            option_type = request.args.get(
                "option_type",
                ""
            ).strip()

            if (
                not expiry
                or not strike
                or not option_type
            ):

                return jsonify({
                    "success": False,
                    "error": (
                        "Expiry, strike and "
                        "option type are required"
                    )
                }), 400

            contract = get_option_contract(
                symbol,
                expiry,
                strike,
                option_type
            )

        if not contract:

            return jsonify({
                "success": False,
                "error": "Contract not found"
            }), 404

        return jsonify({
            "success": True,
            "contract": contract
        })

    except Exception as e:

        print(
            "Contract error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# LTP
# ============================================================

@app.route("/api/ltp")
@admin_required
def api_ltp():

    exchange_segment = request.args.get(
        "exchange_segment",
        ""
    )

    instrument_id = request.args.get(
        "instrument_id",
        ""
    )

    if (
        not exchange_segment
        or not instrument_id
    ):

        return jsonify({
            "success": False,
            "error": (
                "Instrument details missing"
            )
        }), 400

    try:

        client_sessions = app.config.get(
            "CLIENT_SESSIONS",
            {}
        )

        if not client_sessions:

            return jsonify({
                "success": False,
                "error": "No logged clients"
            }), 400

        first_session = next(
            iter(
                client_sessions.values()
            )
        )

        market_xt = first_session[
            "Market_Xt"
        ]

        segment_map = {

            "NSECM": 1,
            "NSE": 1,
            "1": 1,

            "NSEFO": 2,
            "NFO": 2,
            "2": 2,

            "BSECM": 11,
            "BSE": 11,
            "11": 11,

            "BSEFO": 12,
            "BFO": 12,
            "12": 12,
        }

        segment = segment_map.get(
            str(
                exchange_segment
            ).upper()
        )

        if segment is None:

            return jsonify({
                "success": False,
                "error": (
                    "Invalid exchange segment"
                )
            }), 400

        ltp = fetch_ltp(
            market_xt,
            segment,
            int(instrument_id)
        )

        return jsonify({
            "success": True,
            "ltp": ltp
        })

    except Exception as e:

        print(
            "LTP error:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# PLACE ORDER
# ============================================================

@app.route(
    "/api/place-order",
    methods=["POST"]
)
@admin_required
def api_place_order():

    data = request.get_json() or {}

    instrument = (
        data.get("instrument")
        or {}
    )

    side = str(
        data.get(
            "side",
            ""
        )
    ).upper()

    order_type = str(
        data.get(
            "order_type",
            "MARKET"
        )
    ).upper()

    product_type = str(
        data.get(
            "product_type",
            "NRML"
        )
    ).upper()

    limit_price = data.get(
        "limit_price"
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if not instrument:

        return jsonify({
            "success": False,
            "error": "Instrument is required"
        }), 400

    if side not in [
        "BUY",
        "SELL"
    ]:

        return jsonify({
            "success": False,
            "error": "Invalid order side"
        }), 400

    if order_type not in [
        "MARKET",
        "LIMIT"
    ]:

        return jsonify({
            "success": False,
            "error": "Invalid order type"
        }), 400

    if product_type not in [
        "NRML",
        "MIS"
    ]:
        return jsonify({
            "success": False,
            "error": "Invalid product type"
        }), 400

    if order_type == "LIMIT":

        if limit_price in [
            None,
            ""
        ]:

            return jsonify({
                "success": False,
                "error": (
                    "Limit price is required"
                )
            }), 400

        try:

            limit_price = float(
                limit_price
            )

        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "success": False,
                "error": (
                    "Invalid limit price"
                )
            }), 400

    # --------------------------------------------------------
    # Client sessions
    # --------------------------------------------------------

    client_sessions = app.config.get(
        "CLIENT_SESSIONS",
        {}
    )

    if not client_sessions:

        return jsonify({
            "success": False,
            "error": (
                "No clients logged in"
            )
        }), 400

    results = []

    # ========================================================
    # PLACE FOR EVERY ENABLED CLIENT
    # ========================================================

    for client_id, client_session in (
        client_sessions.items()
    ):

        try:

            lots = int(
                client_session.get(
                    "lots",
                    1
                ) or 1
            )

            multiplier = float(
                instrument.get(
                    "multiplier",
                    1
                ) or 1
            )

            quantity = int(
                multiplier * lots
            )

            instrument_id = int(
                instrument[
                    "instrument_id"
                ]
            )

            exchange_segment = (
                instrument.get(
                    "exchange_segment",
                    "NSEFO"
                )
            )

            symbol = instrument.get(
                "symbol",
                ""
            )

            unique_id = (
                f"TD-{client_id}-"
                f"{int(datetime.now().timestamp() * 1000)}"
            )

            # ------------------------------------------------
            # LIMIT
            # ------------------------------------------------

            if order_type == "LIMIT":

                response = place_limit_order(

                    client_session[
                        "Interactive_Xt"
                    ],

                    instrument_id,

                    client_id,

                    quantity,

                    limit_price,

                    side,

                    order_unique_identifier=
                        unique_id,

                    exchange_segment=
                        exchange_segment,

                    product_type=
                        product_type
                )

            # ------------------------------------------------
            # MARKET
            # ------------------------------------------------

            else:

                response = place_market_order(

                    client_session[
                        "Interactive_Xt"
                    ],

                    instrument_id,

                    client_id,

                    quantity,

                    side,

                    order_unique_identifier=
                        unique_id,

                    exchange_segment=
                        exchange_segment,

                    product_type=
                        product_type
                )

            print(
                "\n================ "
                "ORDER API RESPONSE "
                "================"
            )

            print(
                "Client:",
                client_id
            )

            print(
                "Instrument:",
                instrument
            )

            print(
                "Side:",
                side
            )

            print(
                "Quantity:",
                quantity
            )

            print(
                "Order Type:",
                order_type
            )

            print(
                "AETRAM RESPONSE:",
                response
            )

            print(
                "========================================\n"
            )

            # ------------------------------------------------
            # Extract AppOrderID
            # ------------------------------------------------

            app_order_id = None

            if isinstance(
                response,
                dict
            ):

                result = response.get(
                    "result"
                )

                if isinstance(
                    result,
                    dict
                ):

                    app_order_id = (
                        result.get(
                            "AppOrderID"
                        )
                        or
                        result.get(
                            "AppOrderId"
                        )
                        or
                        result.get(
                            "OrderID"
                        )
                        or
                        result.get(
                            "orderID"
                        )
                    )

                app_order_id = (
                    app_order_id
                    or response.get(
                        "AppOrderID"
                    )
                    or response.get(
                        "AppOrderId"
                    )
                    or response.get(
                        "OrderID"
                    )
                    or response.get(
                        "orderID"
                    )
                )

            # ------------------------------------------------
            # Create order book record
            # ------------------------------------------------

            order_record = {

                "app_order_id":
                    str(app_order_id)
                    if app_order_id
                    else "",

                "client_id":
                    client_id,

                "symbol":
                    symbol,

                "side":
                    side,

                "order_side":
                    side,

                "quantity":
                    quantity,

                "price":
                    (
                        limit_price
                        if order_type == "LIMIT"
                        else 0
                    ),

                "average_price":
                    0,

                "order_type":
                    order_type,

                "status":
                    "PendingNew",

                "instrument_id":
                    instrument_id,

                "exchange_segment":
                    exchange_segment,

                "product_type":
                    product_type,

                # IMPORTANT:
                # socket_listener uses "product"
                "product":
                    product_type,

                "is_exit":
                    False,

                "position_id":
                    None,

                "created_at":
                    datetime.now().isoformat()
            }

            # ------------------------------------------------
            # Add to Order Book
            #
            # If socket event arrived first,
            # add_order() merges the pending update.
            # ------------------------------------------------

            stored_order = add_order(
                order_record
            )

            # ------------------------------------------------
            # IMPORTANT RACE CONDITION FIX
            #
            # If AETRAM sent Filled before the
            # order was added, stored_order will
            # already contain status = Filled.
            # Process it now.
            # ------------------------------------------------

            if (
                app_order_id
                and
                str(
                    stored_order.get(
                        "status",
                        ""
                    )
                ).lower()
                == "filled"
            ):

                print(
                    "Filled status was already "
                    "received before add_order(). "
                    "Processing now..."
                )

                process_filled_order(
                    client_id,
                    str(app_order_id)
                )

            results.append({

                "client_id":
                    client_id,

                "success":
                    True,

                "app_order_id":
                    app_order_id,

                "quantity":
                    quantity,

                "response":
                    response
            })

        except Exception as e:

            print(
                f"Order failed for "
                f"{client_id}:",
                e
            )

            results.append({

                "client_id":
                    client_id,

                "success":
                    False,

                "error":
                    str(e)
            })

    successful = [
        r
        for r in results
        if r["success"]
    ]

    return jsonify({

        "success":
            len(successful) > 0,

        "results":
            results
    })


# ============================================================
# ORDER BOOK
# ============================================================

@app.route("/api/orderbook")
@admin_required
def api_orderbook():

    try:

        return jsonify({

            "success":
                True,

            "orders":
                get_orders()
        })

    except Exception as e:

        print(
            "Order book error:",
            e
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ============================================================
# POSITIONS
# ============================================================

@app.route("/api/positions")
@admin_required
def api_positions():

    try:

        return jsonify({

            "success":
                True,

            "positions":
                get_positions()
        })

    except Exception as e:

        print(
            "Positions error:",
            e
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ============================================================
# PANIC SQUARE OFF
# ============================================================

@app.route(
    "/api/panic-squareoff",
    methods=["POST"]
)
@admin_required
def api_panic_squareoff():

    data = request.get_json() or {}

    selected_positions = data.get(
        "positions",
        []
    )

    # --------------------------------------------------------
    # Validate selection
    # --------------------------------------------------------

    if not selected_positions:

        return jsonify({

            "success":
                False,

            "error":
                "No positions selected"

        }), 400

    client_sessions = app.config.get(
        "CLIENT_SESSIONS",
        {}
    )

    if not client_sessions:

        return jsonify({

            "success":
                False,

            "error":
                "No clients logged in"

        }), 400

    positions = get_positions()

    results = []

    # ========================================================
    # PROCESS SELECTED POSITIONS
    # ========================================================

    for position in positions:

        client_id = str(
            position.get(
                "client_id"
            )
        )

        position_id = str(
            position.get(
                "app_order_id"
            )
        )

        # ----------------------------------------------------
        # Check whether this position was selected
        # ----------------------------------------------------

        selected = any(

            isinstance(
                item,
                dict
            )

            and

            str(
                item.get(
                    "client_id"
                )
            )
            == client_id

            and

            str(
                item.get(
                    "app_order_id"
                )
            )
            == position_id

            for item in selected_positions
        )

        if not selected:
            continue

        # ----------------------------------------------------
        # Only OPEN positions can be squared off
        # ----------------------------------------------------

        if str(
            position.get(
                "status",
                ""
            )
        ).upper() != "OPEN":

            continue

        # ----------------------------------------------------
        # Get client session
        # ----------------------------------------------------

        client_session = (
            client_sessions.get(
                client_id
            )
        )

        if not client_session:

            results.append({

                "position_id":
                    position_id,

                "client_id":
                    client_id,

                "success":
                    False,

                "error":
                    "Client session not found"
            })

            continue

        try:

            original_side = str(
                position.get(
                    "side",
                    ""
                )
            ).upper()

            # ------------------------------------------------
            # BUY -> SELL
            # SELL -> BUY
            # ------------------------------------------------

            if original_side == "BUY":

                exit_side = "SELL"

            else:

                exit_side = "BUY"

            quantity = int(
                position.get(
                    "quantity"
                )
                or position.get(
                    "qty"
                )
                or 0
            )

            instrument_id = int(
                position[
                    "instrument_id"
                ]
            )

            exchange_segment = (
                position.get(
                    "exchange_segment"
                )
                or "NSEFO"
            )

            product_type = (
                position.get(
                    "product"
                )
                or position.get(
                    "product_type"
                )
                or "NRML"
            )

            unique_id = (
                f"TD-EXIT-{client_id}-"
                f"{int(datetime.now().timestamp() * 1000)}"
            )

            # ------------------------------------------------
            # Place exit MARKET order
            # ------------------------------------------------

            # ------------------------------------------------
            # Calculate exit LIMIT price
            # ------------------------------------------------

            ltp = float(
                position.get("ltp")
                or 0
            )

            if exit_side == "SELL":

                limit_price = (
                    ltp - 1
                    if ltp > 1
                    else ltp
                )

            else:

                limit_price = ltp + 1

            # ------------------------------------------------
            # Place exit LIMIT order
            # ------------------------------------------------

            response = place_limit_order(

                client_session[
                    "Interactive_Xt"
                ],

                instrument_id,

                client_id,

                quantity,

                limit_price,

                exit_side,

                order_unique_identifier=
                unique_id,

                exchange_segment=
                exchange_segment,

                product_type=
                product_type
            )

            print(
                "\n================ "
                "EXIT ORDER RESPONSE "
                "================"
            )

            print(
                "Client:",
                client_id
            )

            print(
                "Position:",
                position_id
            )

            print(
                "Exit Side:",
                exit_side
            )

            print(
                "Quantity:",
                quantity
            )

            print(
                "Response:",
                response
            )

            print(
                "========================================\n"
            )

            # ------------------------------------------------
            # Extract exit AppOrderID
            # ------------------------------------------------

            exit_order_id = None

            if isinstance(
                response,
                dict
            ):

                result = response.get(
                    "result"
                )

                if isinstance(
                    result,
                    dict
                ):

                    exit_order_id = (
                        result.get(
                            "AppOrderID"
                        )
                        or
                        result.get(
                            "AppOrderId"
                        )
                        or
                        result.get(
                            "OrderID"
                        )
                        or
                        result.get(
                            "orderID"
                        )
                    )

                exit_order_id = (
                    exit_order_id
                    or response.get(
                        "AppOrderID"
                    )
                    or response.get(
                        "AppOrderId"
                    )
                    or response.get(
                        "OrderID"
                    )
                    or response.get(
                        "orderID"
                    )
                )

            # ------------------------------------------------
            # Exit order ID is required
            # ------------------------------------------------

            if not exit_order_id:

                results.append({

                    "position_id":
                        position_id,

                    "client_id":
                        client_id,

                    "success":
                        False,

                    "error":
                        "Exit order AppOrderID not received"
                })

                continue

            # ------------------------------------------------
            # Add exit order to Order Book
            # ------------------------------------------------

            exit_order_record = {

                "app_order_id":
                    str(
                        exit_order_id
                    ),

                "client_id":
                    client_id,

                "symbol":
                    position.get(
                        "symbol",
                        ""
                    ),

                "side":
                    exit_side,

                "order_side":
                    exit_side,

                "quantity":
                    quantity,

                "price":
                    limit_price,

                "average_price":
                      0,

                "order_type":
                    "LIMIT",

                "status":
                    "PendingNew",

                "instrument_id":
                    instrument_id,

                "exchange_segment":
                    exchange_segment,

                "product_type":
                    product_type,

                "product":
                    product_type,

                # IMPORTANT
                "is_exit":
                    True,

                # Original position
                "position_id":
                    position_id,

                "created_at":
                    datetime.now().isoformat()
            }

            # ------------------------------------------------
            # Add exit order
            #
            # If Filled arrived before this,
            # pending update will be merged.
            # ------------------------------------------------

            stored_exit_order = add_order(
                exit_order_record
            )

            # ------------------------------------------------
            # EXIT RACE CONDITION FIX
            # ------------------------------------------------

            if (
                str(
                    stored_exit_order.get(
                        "status",
                        ""
                    )
                ).lower()
                == "filled"
            ):

                print(
                    "Exit Filled status was received "
                    "before add_order(). "
                    "Processing exit now..."
                )

                process_filled_order(
                    client_id,
                    str(exit_order_id)
                )

            results.append({

                "position_id":
                    position_id,

                "client_id":
                    client_id,

                "success":
                    True,

                "exit_order_id":
                    exit_order_id
            })

        except Exception as e:

            print(
                f"Square off failed "
                f"for {client_id}:",
                e
            )

            results.append({

                "position_id":
                    position_id,

                "client_id":
                    client_id,

                "success":
                    False,

                "error":
                    str(e)
            })

    successful = [
        r
        for r in results
        if r["success"]
    ]

    return jsonify({

        "success":
            len(successful) > 0,

        "results":
            results
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="0.0.0.0",

        port=5000,

        use_reloader=False
    )