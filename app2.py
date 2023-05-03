from flask import Flask, request
from threading import Thread
from pybit.unified_trading import HTTP
from time import sleep
import requests
from gunicorn.app.base import BaseApplication
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1101655744677425293/J2e5vY2wVA6kCO9o2SSjrZ7Wi3s0PPs7mM1sUW1tNOvLK6P4yikFaU7oEYjuaRdEz8zF"


def send_discord_message(content):
    requests.post(DISCORD_WEBHOOK_URL, json={"content": content})


def pnl_report(session):
    pnl = session.get_pnl(category="linear", symbol="ETHUSDT")
    daily_pnl = pnl["result"]["dailyPnl"]
    closed_pnl = pnl["result"]["closedPnl"]
    all_time_pnl = daily_pnl + closed_pnl

    message = f"Daily PnL: {daily_pnl}\nAll Time PnL: {all_time_pnl}\nClosed PnL: {closed_pnl}"
    send_discord_message(message)


@app.route('/webhook', methods=['POST'])
def webhook():
    logging.info("Received webhook")
    data = request.get_json()

    try:
        execute_trading_strategy(data)
    except Exception as e:
        send_discord_message(f"Error executing trading strategy: {e}")
        logging.exception("Error executing trading strategy")
        raise e

    return {'success': True}


def execute_trading_strategy(data):
    session = HTTP(
        testnet=False,
        api_key="RkBBUvhqHenWNQP1lw",
        api_secret="oOTfYyo49Dd3GF24wZNf1zN3B1sGzW04Ig9f",
    )

    current_price = float(session.get_tickers(
        category="inverse",
        symbol="ETHUSDT",
    )["result"]["list"][0]["markPrice"])

    wallet_balance = session.get_wallet_balance(
        accountType="UNIFIED",
        coin="USDT",
    )

    total_balance = float(wallet_balance["result"]["list"][0]["totalAvailableBalance"])

    order_qty = (total_balance / current_price) * 5
    order_qty = round(order_qty, 4)

    side = data["side"]

    take_profit_price = current_price * 1.005 if side == "Buy" else current_price * 0.995
    take_profit_price = round(take_profit_price, 2)

    open_positions = session.get_positions(category="linear", symbol="ETHUSDT")["result"]["list"]

    if not open_positions:
        order_result = session.place_order(
            category="linear",
            symbol="ETHUSDT",
            side=side,
            orderType="Market",
            qty=order_qty,
            takeProfit=take_profit_price,
            tpTriggerBy="MarkPrice",
        )

        send_discord_message(f"Order placed:\n{order_result}")

        pnl_report(session)

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.application = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    send_discord_message("Bot started")  # Send a message when the bot starts

    options = {
        'bind': '0.0.0.0:80',
        'workers': 1,
        'threads': 2,
    }

    StandaloneApplication(app, options).run()

    try:
        while True:
            sleep(86400)  # Sleep for a day
            send_discord_message("Bot is still running")
    except:
        send_discord_message("Bot stopped")
        raise

