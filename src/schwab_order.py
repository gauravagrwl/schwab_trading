from decimal import Decimal, ROUND_HALF_DOWN, ROUND_HALF_UP

from pydantic import BaseModel
from schwab import auth
from schwab.orders.common import Duration, Session
from schwab.orders.common import first_triggers_second
from schwab.orders.equities import equity_buy_limit, equity_sell_limit

from src import logger, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, TOKEN_PATH


class Order(BaseModel):
    symbol: str
    amount: Decimal  # Total dollar amount to spend
    percentage: Decimal  # Could be used for portfolio sizing
    qty: int  # Backup if not using 'amount'
    repeat: int = 1


# Schwab Config


def place_schwab_order(order: Order):
    try:
        # Initialize Client
        client = auth.easy_client(api_key=CLIENT_ID, app_secret=CLIENT_SECRET, callback_url=REDIRECT_URI,
                                  token_path=TOKEN_PATH, interactive=False)

        if order.symbol is None:
            return {"error": "Could not fetch price"}
        else:
            r = 0
            while r < order.repeat:
                logger.info(f"Place Order: {order} - Order Number {r + 1}")
                execute_schwab_order(order, client)
            return {"msg": "Order placed successfully"}
    except Exception as e:
        logger.error(e)
        return {"error": str(e)}


def execute_schwab_order(order: Order, client):
    # 2. Get Current Price
    quote_res = client.get_quotes([order.symbol])
    if not quote_res.status_code == 200:
        raise Exception(quote_res.text)

    current_price = quote_res.json()[order.symbol]['quote']['lastPrice']
    # Set your buy price at every execution

    # shares_to_buy = order.qty
    shares_to_buy = int(order.amount / Decimal(str(current_price)))
    # Use user_order.qty if amount was not provided
    final_qty = shares_to_buy if shares_to_buy < order.qty else order.qty

    # Define price
    buy_price = current_price
    buy_price = Decimal(str(current_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)
    pct_increase = Decimal(1 + (order.percentage / 100))

    sell_price = (buy_price * pct_increase).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    place_buy_trigger_sell(order.symbol, final_qty, buy_price, sell_price, client)


def place_buy_trigger_sell(symbol, qty, buy_price, sell_price, client):
    # Leg 1: The Buy Order (The Trigger)
    # We use a Limit order to catch that "Red Tick"
    buy_leg = equity_buy_limit(symbol, qty, buy_price).set_duration(Duration.DAY).set_session(Session.NORMAL)

    # Leg 2: The Sell Order (The Profit Taker)
    # This order is only placed AFTER the buy fills
    sell_leg = equity_sell_limit(symbol, qty, sell_price).set_duration(Duration.DAY).set_session(Session.NORMAL)

    # Link them: 1st triggers 2nd
    fts_order = first_triggers_second(buy_leg, sell_leg)

    # Get Account Hash and Place the composite order
    account_hash = client.get_account_numbers().json()[0]['hashValue']
    response = client.place_order(account_hash, fts_order.build())
    logger.info(response)
