#!/usr/bin/env python3
"""
test_telegram.py — CLI tool to test Telegram Bot connection and push notification.

Usage:
    uv run python scripts/test_telegram.py

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env and sends a test message.
"""
import asyncio
import sys

from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.services.alerting.telegram_bot import TelegramService


async def main() -> None:
    print("🤖 Crypto MAS — Telegram Bağlantı Test Aracı")
    print("---------------------------------------------")
    settings = get_settings()

    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        print("❌ HATA: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID tanımlı değil!")
        print("   Lütfen .env dosyanıza bu değerleri ekleyin.")
        sys.exit(1)

    print(f"🔹 Bot Token : {token[:8]}...{token[-4:]}")
    print(f"🔹 Chat ID   : {chat_id}")
    print("📨 Test mesajı gönderiliyor...")

    service = TelegramService(token=token, chat_id=chat_id)
    test_msg = (
        "🏓 <b>Crypto MAS — Telegram Test Bildirimi</b>\n\n"
        "✅ <b>Tebrikler!</b> Bot bağlantınız ve yetkilendirmeniz sorunsuz çalışıyor.\n"
        "⚙️ Artık bota <code>/help</code> yazarak tüm komutlara erişebilirsiniz."
    )
    await service.send(test_msg)
    print("✅ İşlem tamamlandı! Lütfen Telegram uygulamanızı kontrol edin.")


if __name__ == "__main__":
    asyncio.run(main())
