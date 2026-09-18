from .Connect import XTSConnect

def place_limit_order(
    bt,
    ins_token,
    cl_id,
    qty,
    lmt_price,
    side,
    order_unique_identifier=None,
    exchange_segment="NSEFO",
    product_type="NRML"
):
    try:
        response = bt.place_order(
            exchangeSegment=exchange_segment,
            exchangeInstrumentID=int(ins_token),
            productType=product_type,
            orderType="LIMIT",
            orderSide=side,
            timeInForce="DAY",
            disclosedQuantity=0,
            orderQuantity=int(qty),
            limitPrice=float(lmt_price),
            stopPrice=0,
            orderUniqueIdentifier=(
                order_unique_identifier
                or f"{cl_id}_limit"
            ),
            apiOrderSource="WEBAPI"
        )

        return response

    except Exception as e:
        raise Exception(
            f"Limit order failed for {cl_id}: {str(e)}"
        )


def place_market_order(
    bt,
    ins_token,
    cl_id,
    qty,
    side,
    exchange_segment="NSEFO",
    product_type="NRML",
    order_unique_identifier=None
):
    try:
        response = bt.place_order(
            exchangeSegment=exchange_segment,
            exchangeInstrumentID=int(ins_token),
            productType=product_type,
            orderType="MARKET",
            orderSide=side,
            timeInForce="DAY",
            disclosedQuantity=0,
            orderQuantity=int(qty),
            limitPrice=0,
            stopPrice=0,
            orderUniqueIdentifier=(
                order_unique_identifier
                or f"{cl_id}_market"
            ),
            apiOrderSource="WEBAPI"
        )

        return response

    except Exception as e:
        raise Exception(
            f"Market order failed for {cl_id}: {str(e)}"
        )


def place_square_off_order(
    bt,
    ins_token,
    cl_id,
    qty,
    exchange_segment="NSEFO",
    product_type="NRML"
):
    return place_market_order(
        bt=bt,
        ins_token=ins_token,
        cl_id=cl_id,
        qty=qty,
        side="SELL",
        exchange_segment=exchange_segment,
        product_type=product_type,
        order_unique_identifier=f"{cl_id}_squareoff"
    )


def place_square_off_buy_order(
    bt,
    ins_token,
    cl_id,
    qty,
    exchange_segment="NSEFO",
    product_type="NRML"
):
    return place_market_order(
        bt=bt,
        ins_token=ins_token,
        cl_id=cl_id,
        qty=qty,
        side="BUY",
        exchange_segment=exchange_segment,
        product_type=product_type,
        order_unique_identifier=f"{cl_id}_squareoff_buy"
    )
# def place_square_off_buy_order(bt, ins_token, cl_id, qty):
#     """
#     Place a square-off order (BUY) to close short positions.
#     """
#     return bt.place_order(
#         exchangeSegment="NSEFO",
#         exchangeInstrumentID=ins_token,
#         productType="NRML",
#         orderType="MARKET",
#         orderSide="BUY",
#         timeInForce="DAY",
#         disclosedQuantity=0,
#         orderQuantity=qty,
#         limitPrice=0,
#         stopPrice=0,
#         orderUniqueIdentifier=f"{cl_id}_squareoff_buy",
#         apiOrderSource="WEBAPI"
#     )

def cancel_order(bt, order_id, cl_id):
    """
    Cancel an order by order_id.
    """
    return bt.cancel_order(
        appOrderID=order_id,
        orderUniqueIdentifier=f"{cl_id}_cancel"
    )

def modify_order(bt, order_id, cl_id, new_price, new_qty):
    """
    Modify an existing limit order.
    bt: Interactive_Xt client
    order_id: AppOrderID of the order to modify
    cl_id: client_id
    new_price: new limit price
    new_qty: required quantity (must be >= 1)
    """
    return bt.modify_order(
        appOrderID=order_id,
        modifiedProductType="NRML",
        modifiedOrderType="LIMIT",
        modifiedOrderQuantity=new_qty,
        modifiedDisclosedQuantity=0,
        modifiedLimitPrice=new_price,
        modifiedStopPrice=0,
        modifiedTimeInForce="DAY",
        orderUniqueIdentifier=f"{cl_id}_modify",
        clientID=cl_id
    )

def place_bracket_order(
        bt,
        exchange_segment,
        ins_token,
        cl_id,
        qty,
        side,
        limit_price,
        square_off,
        stop_loss,
        trailing_sl=0,
        is_pro_order=False
):
    """
    Place a Bracket Order (BO).

    Parameters:
    bt              : Interactive_Xt client
    ins_token       : instrument token
    cl_id           : client id
    qty             : quantity
    side            : 'BUY' or 'SELL'
    limit_price     : entry price
    square_off      : target points
    stop_loss       : stoploss points
    trailing_sl     : trailing SL points
    is_pro_order    : True/False
    """

    return bt.place_bracketorder(
        exchangeSegment=exchange_segment,
        exchangeInstrumentID=ins_token,
        orderType="LIMIT",          # Usually LIMIT for BO
        orderSide=side,
        disclosedQuantity=0,
        orderQuantity=qty,
        limitPrice=limit_price,
        squarOff=square_off,
        stopLossPrice=stop_loss,
        trailingStoploss=trailing_sl,
        isProOrder=is_pro_order,
        apiOrderSource="WEBAPI",
        orderUniqueIdentifier=f"{cl_id}_bo"
    )

def cancel_bracket_order(bt, app_order_id):
    """
    Cancel entire bracket order.
    """

    return bt.bracketorder_cancel(
        appOrderID=app_order_id
    )