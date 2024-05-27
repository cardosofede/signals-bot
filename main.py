import asyncio
import logging
from datetime import datetime, timedelta

import pandas as pd
import pandas_ta as ta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from geckoterminal_py import GeckoTerminalAsyncClient
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import (
    CHANNEL_ID_MAPPING,
    CHAT_ID,
    MIN_POOL_AGE,
    RESERVE_FILTER,
    TOKEN,
    TREND_FOLLOWER_CONFIG,
    VOLUME_FILTER,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

gecko_client = GeckoTerminalAsyncClient()
bot = Bot(token=TOKEN)
scheduler = AsyncIOScheduler()


async def fetch_top_pools(network):
    # Fetching top pools for the given network
    candles = await gecko_client.get_top_pools_by_network(network)
    candles["volume_usd_h24"] = candles["volume_usd_h24"].astype(float)
    candles["reserve_in_usd"] = candles["reserve_in_usd"].astype(float)
    candles["pool_created_at"] = pd.to_datetime(candles["pool_created_at"])
    candles["close"] = candles["base_token_price_usd"].astype(float)
    return candles


def apply_filters(pools_df: pd.DataFrame):
    # Applying filtering logic
    now_utc = pd.Timestamp(datetime.now(), tz="UTC")
    volume_condition = pools_df["volume_usd_h24"] > VOLUME_FILTER
    age_condition = (now_utc - pools_df["pool_created_at"]) > timedelta(
        days=MIN_POOL_AGE
    )
    reserves_filter = pools_df["reserve_in_usd"] > RESERVE_FILTER
    return pools_df[volume_condition & age_condition & reserves_filter]


async def fetch_historical_candles(pool_info):
    # Fetching historical candles for the given pool
    return await gecko_client.get_ohlcv(
        pool_info["network_id"], pool_info["address"], timeframe="4h"
    )


def apply_strategy(candles, pool_info):
    # Applying strategy logic to generate signals
    candles["slow_ma"] = ta.sma(
        candles["close"], length=TREND_FOLLOWER_CONFIG["slow_ma"]
    )
    candles["mid_ma"] = ta.sma(candles["close"], length=TREND_FOLLOWER_CONFIG["mid_ma"])
    candles["fast_ma"] = ta.sma(
        candles["close"], length=TREND_FOLLOWER_CONFIG["fast_ma"]
    )

    last_row = candles.iloc[-1].replace(".", "\.")
    close = f"{last_row['close']:.8f}".replace(".", "\.")
    liquidity = f"{pool_info['reserve_in_usd']:.2f}".replace(".", "\.")
    fdv = pool_info["fdv_usd"].replace(".", "\.")
    market_cap = (
        "N\/A"
        if pd.isnull(pool_info["market_cap_usd"])
        else f"{pool_info['market_cap_usd']:.2f}".replace(".", "\.")
    )
    vol_24h = f"{pool_info['volume_usd_h24']:.2f}".replace(".", "\.")
    dex_id = pool_info["dex_id"].replace("_", "\_")
    buys_txn = pool_info["transactions_h24_buys"]
    sells_txn = pool_info["transactions_h24_sells"]
    name = pool_info["name"].replace("-", "\-").replace(".", "\.")
    reason = f"""The current price of the token is above the 150 MA and the 20 MA is above the 75 MA\. This is a bullish signal\."""

    try:
        if (
            last_row["fast_ma"] > last_row["mid_ma"]
            and last_row["close"] > last_row["slow_ma"]
        ):
            return f"""
🚀 *Trading Signal Alert\\!* 🚀

📈 *BULLISH CALL detected\\!*\n\n
*Ticker:* {name}
*Price:* \$ {close}
*Reason:* {reason}
*DEX:* {dex_id}
*Liquidity:* \$ {liquidity}
*FDV:* \$ {fdv}
*Market Cap:* \$ {market_cap}
*24h Volume:* \$ {vol_24h}
*Buys Txn:* {buys_txn}
*Sells Txn:* {sells_txn}

🔗 [View on GeckoTerminal](https://geckoterminal\\.com/{pool_info["network_id"]}/pools/{pool_info["address"]})
        """
    except Exception as e:
        logging.error(e)
    return None


async def process_signals(network):
    top_pools = await fetch_top_pools(network)
    filtered_pools = apply_filters(top_pools)
    for i, row in filtered_pools.iterrows():
        candles = await fetch_historical_candles(row)
        signal = apply_strategy(candles, row)
        if signal:
            channel_id = CHANNEL_ID_MAPPING[network]
            await bot.send_message(
                chat_id=CHAT_ID,
                text=signal,
                parse_mode="MarkdownV2",
                message_thread_id=channel_id,
            )


async def scheduled_task():
    for network in CHANNEL_ID_MAPPING.keys():
        await process_signals(network)
        await asyncio.sleep(1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_text = """
🚀 **Welcome to ELUUP Signal Bot\!** Your personal AI trading assistant, here to organize and streamline your trading life\.
🧠 For more information, please join the groups below to start receiving signals\:
"""
    await update.message.reply_text(reply_text, parse_mode="MarkdownV2")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)
    scheduler.add_job(scheduled_task, "interval", seconds=10)
    scheduler.start()
    # Execute the task immediately after starting the scheduler

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
