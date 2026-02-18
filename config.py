import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_PASS = os.environ.get("ADMIN_PASS", "adm9912")

FREE_MSG = 15
FREE_IMG = 1
PREM_MSG = 999
PREM_IMG = 20
PREM_PRICE = 100
PREM_DAYS = 30

MODELS = {
    "gpt4o_mini": {"name": "⚡ GPT-4o Mini", "id": "gpt-4o-mini", "prem": False},
    "gpt4o": {"name": "🧠 GPT-4o", "id": "gpt-4o", "prem": False},
    "gpt4_turbo": {"name": "🚀 GPT-4 Turbo", "id": "gpt-4-turbo", "prem": True},
    "gpt35": {"name": "💬 GPT-3.5", "id": "gpt-3.5-turbo", "prem": False},
}

API_URLS = [
    "https://api.openai4.chat/v1/chat/completions",
    "https://api.chatanywhere.tech/v1/chat/completions",
    "https://free.gpt.ge/v1/chat/completions",
]
