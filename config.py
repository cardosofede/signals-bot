import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

VOLUME_FILTER = 100000
MIN_POOL_AGE = 30
RESERVE_FILTER = 50000
TREND_FOLLOWER_CONFIG = {
    "slow_ma": 150,
    "mid_ma": 75,
    "fast_ma": 20,
}
CHAT_ID = -1002106189523
CHANNEL_ID_MAPPING = {
    "eth": 2,
    "bsc": 10,
    "base": 4,
    "solana": 6,
    "blast": 24,
    "polygon_pos": 12,
    "arbitrum": 16,
    "optimism": 18,
    "pulsechain": 20,
    "cro": 22,
}
