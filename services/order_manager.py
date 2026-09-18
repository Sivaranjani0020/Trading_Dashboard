"""order_manager.py"""
import time

from helper_funct.client_order_funct import (
    place_limit_order,
    place_market_order
)

from services.orderbook_manager import add_order
from services.position_manager import add_position
from services.logger import log_program_event


def _get_lots(client_session):
    try:
        return max(1, int(client_session.get("lots", 1)))
    except Exception:
        return 1


def calculate_quantity(multiplier, lots):
    return int(multiplier) * int(lots)


def place_dashboard_orders(
    client_sessions,
    instrument,
    side,
    order_type="MARKET",
    limit_price=None,
    product_type="NRML"
):
    """
    Place the selected instrument order for every enabled client.

    client_sessions:
        {
            client_id: {
                "Interactive_Xt": ...,
                "Market_Xt": ...,
                "lots": ...
            }
        }

    instrument:
        {
            "instrument_id": ...,
            "symbol": ...,
            "exchange_segment": ...,
            "multiplier": ...,
            "tick_size": ...
        }
    """

    results = []

    instrument_id = int(instrument["instrument_id"])
    symbol = instrument["symbol"]
    exchange_segment = instrument.get("exchange_segment", "NSEFO")
    multiplier = int(instrument.get("multiplier", 1))

    side = str(side).upper()
    order_type = str(order_type).upper()
    product_type = str(product_type).upper()

    if side not in ("BUY", "SELL"):
        raise ValueError("Invalid order side")

    if order_type not in ("MARKET", "LIMIT"):
        raise ValueError("Invalid order type")

    if product_type not in ("NRML", "MIS"):
        raise ValueError("Invalid product type")

    if order_type == "LIMIT":
        if limit_price is None:
            raise ValueError("Limit price is required")

        limit_price = float(limit_price)

        if limit_price <= 0:
            raise ValueError("Invalid limit price")

    for client_id, session_data in client_sessions.items():

        try:
            interactive_xt = session_data["Interactive_Xt"]

            lots = _get_lots(session_data)
            quantity = calculate_quantity(multiplier, lots)

            unique_id = (
                f"TD_{client_id}_{int(time.time() * 1000)}"
            )

            if order_type == "MARKET":

                response = place_market_order(
                    interactive_xt,
                    instrument_id,
                    client_id,
                    quantity,
                    side,
                    exchange_segment=exchange_segment,
                    product_type=product_type,
                    order_unique_identifier=unique_id
                )

            else:

                response = place_limit_order(
                    interactive_xt,
                    instrument_id,
                    client_id,
                    quantity,
                    limit_price,
                    side,
                    order_unique_identifier=unique_id,
                    exchange_segment=exchange_segment,
                    product_type=product_type
                )

            if not response:
                raise Exception("Empty order response")

            result = response.get("result", response)

            app_order_id = (
                result.get("AppOrderID")
                or result.get("AppOrderId")
                or result.get("OrderID")
                or result.get("orderID")
            )

            order_record = {
                "client_id": client_id,
                "app_order_id": str(app_order_id) if app_order_id else unique_id,
                "instrument_id": instrument_id,
                "symbol": symbol,
                "side": side,
                "qty": quantity,
                "lots": lots,
                "order_type": order_type,
                "price": limit_price if order_type == "LIMIT" else 0,
                "entry_price": limit_price if order_type == "LIMIT" else 0,
                "status": "PendingNew",
                "product": product_type,
                "exchange_segment": exchange_segment
            }

            add_order(order_record)

            # Position is created immediately as PendingNew.
            # Socket will change it to Filled/Open after confirmation.
            add_position({
                "client_id": client_id,
                "app_order_id": order_record["app_order_id"],
                "instrument_id": instrument_id,
                "symbol": symbol,
                "side": side,
                "qty": quantity,
                "entry_price": order_record["entry_price"],
                "ltp": order_record["entry_price"],
                "pnl": 0,
                "status": "PendingNew",
                "product": product_type,
            })

            results.append({
                "client_id": client_id,
                "app_order_id": order_record["app_order_id"],
                "status": "success",
                "quantity": quantity,
                "response": response
            })

            log_program_event(
                client_id,
                "Dashboard order placed",
                {
                    "symbol": symbol,
                    "instrument_id": instrument_id,
                    "side": side,
                    "quantity": quantity,
                    "order_type": order_type
                }
            )

        except Exception as e:

            results.append({
                "client_id": client_id,
                "status": "failed",
                "error": str(e)
            })

            log_program_event(
                client_id,
                "Dashboard order failed",
                {
                    "symbol": symbol,
                    "side": side,
                    "error": str(e)
                }
            )

    return results