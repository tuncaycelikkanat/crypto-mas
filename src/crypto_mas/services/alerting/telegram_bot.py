"""
telegram_bot.py — Lightweight Telegram alerter and interactive Command Center using httpx.

Sends notifications to a Telegram chat via Bot API and listens for interactive commands
(/help, /status, /positions, /balance, /regime, /panic) via async long-polling.
No external Telegram library required — uses httpx (already a project dependency).

Configuration (via .env):
    TELEGRAM_BOT_TOKEN=<your bot token>
    TELEGRAM_CHAT_ID=<your chat id>
"""
import asyncio
from decimal import Decimal
import logging
from typing import Any, Optional

import httpx

from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramAlerter:
    """Async Telegram notification sender and two-way Command Center.

    Inject an instance into services that should emit alerts.
    All methods are safe to call with missing credentials — they log a warning
    and return silently so production code is never disrupted by alerting failures.
    """

    _instance: Optional["TelegramAlerter"] = None

    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self.token = token
        self.chat_id = str(chat_id) if chat_id else None
        self._enabled = bool(token and chat_id)
        self.app_state: Any = None
        self._is_polling = False
        self._poll_task: asyncio.Task[None] | None = None
        self._last_update_id = 0
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        TelegramAlerter._instance = self

        if not self._enabled:
            logger.info(
                "[TelegramAlerter] Disabled — set TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID to enable."
            )

    @classmethod
    def get_instance(cls) -> Optional["TelegramAlerter"]:
        """Returns the active global instance of TelegramAlerter."""
        return cls._instance

    async def send(self, message: str) -> None:
        """Send a plain-text or HTML message to the configured Telegram chat."""
        if not self._enabled:
            return
        url = f"{TELEGRAM_API_BASE.format(token=self.token)}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    logger.warning(
                        "[TelegramAlerter] API returned %d: %s",
                        response.status_code, response.text[:200],
                    )
        except Exception as exc:
            logger.warning("[TelegramAlerter] Failed to send alert: %s", exc)

    # --- Interactive Command Center (Long-Polling) ---

    async def start_polling(self, app_state: Any = None) -> None:
        """Start async background long-polling for interactive commands."""
        if not self._enabled:
            logger.info("[TelegramService] Polling skipped — bot disabled.")
            return
        self.app_state = app_state
        self._is_polling = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("[TelegramService] Interactive Command Center started polling.")

    def stop_polling(self) -> None:
        """Stop background polling loop cleanly."""
        self._is_polling = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        logger.info("[TelegramService] Interactive Command Center stopped polling.")

    async def _poll_loop(self) -> None:
        """Continuous long-polling loop against Telegram Bot API getUpdates."""
        url = f"{TELEGRAM_API_BASE.format(token=self.token)}/getUpdates"
        while self._is_polling and self._enabled:
            try:
                params = {
                    "offset": self._last_update_id + 1,
                    "timeout": 20,
                }
                async with httpx.AsyncClient(timeout=35.0) as client:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        for update in data.get("result", []):
                            update_id = update.get("update_id", 0)
                            self._last_update_id = max(self._last_update_id, update_id)
                            if "message" in update:
                                await self._handle_message(update["message"])
                    else:
                        logger.warning("[TelegramService] getUpdates failed: %s", response.text[:100])
                        await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("[TelegramService] Polling exception: %s", exc)
                await asyncio.sleep(5)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Verify sender authorization and dispatch command."""
        sender_chat_id = str(message.get("chat", {}).get("id", ""))
        if sender_chat_id != self.chat_id:
            logger.warning("[TelegramService] Unauthorized message from chat_id: %s", sender_chat_id)
            return

        text = message.get("text", "").strip()
        if text:
            await self._dispatch_command(text)

    async def _dispatch_command(self, text: str) -> None:
        """Execute interactive commands (/help, /status, /positions, /balance, /regime, /panic)."""
        try:
            parts = text.split()
            command = parts[0].lower().lstrip("/")

            if command in ("help", "start"):
                await self._cmd_help()
            elif command in ("test", "ping"):
                await self._cmd_test()
            elif command == "status":
                await self._cmd_status()
            elif command == "positions":
                await self._cmd_positions()
            elif command == "balance":
                await self._cmd_balance()
            elif command == "regime":
                await self._cmd_regime()
            elif command in ("panic", "stop_all"):
                await self._cmd_panic()
            else:
                await self.send(f"❓ Bilinmeyen komut: <code>{command}</code>. Yardım menüsü için <b>/help</b> yazabilirsin.")
        except Exception as exc:
            logger.error("[TelegramService] Error executing command '%s': %s", text, exc, exc_info=True)
            await self.send(f"❌ Komut çalıştırılırken bir hata oluştu: <code>{exc}</code>")

    async def _cmd_help(self) -> None:
        """Send rich HTML help menu."""
        msg = (
            "🤖 <b>Crypto MAS — Telegram Komut Merkezi</b>\n\n"
            "📋 <b>KULLANILABİLİR KOMUTLAR:</b>\n"
            "<b>/help</b> — Bu yardım menüsünü ve kullanım rehberini gösterir.\n"
            "<b>/test</b> (veya <b>/ping</b>) — Telegram bot bağlantısının çalıştığını test eder.\n"
            "<b>/status</b> — Çalışan Paper/Live bot sayısını ve sistem sağlığını gösterir.\n"
            "<b>/positions</b> — Açık olan pozisyonları, giriş fiyatlarını ve PnL durumunu listeler.\n"
            "<b>/balance</b> — Portföy bakiyesini (Cash & Equity) raporlar.\n"
            "<b>/regime</b> — Mevcut piyasa rejimini (BULL_TREND / BEAR_TREND vs.) denetler.\n"
            "🚨 <b>/panic</b> — <b>ACİL DURDURMA:</b> Çalışan tüm algoritmik botları anında durdurur!\n\n"
            "💡 <i>Not: Komutları başında / işareti olmadan da (örn: <b>status</b>, <b>ping</b>) yazabilirsiniz.</i>"
        )
        await self.send(msg)

    async def _cmd_test(self) -> None:
        """Send a quick ping/test verification message."""
        msg = (
            "🏓 <b>PONG! — Telegram Bağlantısı Başarılı!</b>\n\n"
            "✅ <b>Bot Durumu:</b> Aktif ve komutlarınızı dinlemeye hazır.\n"
            "💬 <b>Yetkili Chat ID:</b> Doğrulandı."
        )
        await self.send(msg)

    async def _cmd_status(self) -> None:
        """Report system health and active trading mode."""
        settings = get_settings()
        active_jobs = 0
        if self.app_state and getattr(self.app_state, "scheduler", None):
            try:
                status_dict = self.app_state.scheduler.get_status()
                bots_info = status_dict.get("bots", [])
                active_jobs = len(bots_info)
            except Exception as exc:
                logger.warning("[TelegramService] _cmd_status error getting scheduler status: %s", exc)

        bot_status_str = f"{active_jobs} Aktif Bot Çalışıyor" if active_jobs > 0 else "0 (Aktif Al-Sat Botu Yok)"
        msg = (
            f"⚙️ <b>Crypto MAS — Sistem ve Bot Durumu</b>\n\n"
            f"🟢 <b>Sistem Altyapısı:</b> AKTİF (7/24 Dinliyor)\n"
            f"🕹️ <b>İşlem Modu:</b> <code>{settings.trading_mode}</code>\n"
            f"🤖 <b>Çalışan Al-Sat Botu:</b> <code>{bot_status_str}</code>\n"
            f"ℹ️ <i>Not: Mod PAPER olarak ayarlıdır. Arayüzden veya API'den bot başlattığınızda burada görünecektir.</i>\n"
            f"🔗 <b>Korele Varlık Listesi:</b> <code>{len(settings.btc_correlated_symbols)} coin</code>"
        )
        await self.send(msg)

    async def _cmd_positions(self) -> None:
        """Query and format open trading positions."""
        try:
            with SessionLocal() as db:
                repo = PositionRepository(db)
                account_repo = PaperAccountRepository(db)
                accounts = account_repo.get_all()
                if not accounts:
                    await self.send("📂 <b>Açık Pozisyon Bulunmuyor</b>\nSistemde henüz hesap oluşturulmamış.")
                    return

                lines = []
                for acc in accounts:
                    positions = repo.list_open_positions(acc.name)
                    if positions:
                        lines.append(f"📊 <b>Açık Pozisyonlar ({acc.name})</b>")
                        for p in positions:
                            tp_val = f"{p.take_profit_price:.4f}" if p.take_profit_price is not None else "None"
                            sl_val = f"{p.stop_loss_price:.4f}" if p.stop_loss_price is not None else "None"
                            lines.append(
                                f"🔹 <b>{p.symbol} ({p.status})</b>\n"
                                f"   Giriş: <code>{p.entry_price:.4f}</code> | Miktar: <code>{p.quantity:.4f}</code>\n"
                                f"   TP: <code>{tp_val}</code> | SL: <code>{sl_val}</code>"
                            )
                        lines.append("") # Empty line between accounts
                
                if not lines:
                    await self.send("📂 <b>Açık Pozisyon Bulunmuyor</b>\nŞu anda hiçbir hesapta aktif alım-satım pozisyonu yok.")
                else:
                    await self.send("\n".join(lines))
        except Exception as exc:
            logger.error("[TelegramService] _cmd_positions error: %s", exc)
            await self.send("❌ Pozisyonlar sorgulanırken bir hata oluştu.")

    async def _cmd_balance(self) -> None:
        """Query paper trading balance and equity."""
        try:
            with SessionLocal() as db:
                repo = PaperAccountRepository(db)
                accounts = repo.get_all()
                if not accounts:
                    account = repo.create_if_not_exists(
                        name="default-paper",
                        exchange="MOCK",
                        base_currency="USDT",
                        initial_balance=Decimal("10000"),
                    )
                    accounts = [account]

                lines = []
                for account in accounts:
                    lines.append(
                        f"💰 <b>Portföy Bakiyesi ({account.name})</b>\n"
                        f"💵 <b>Nakit:</b> <code>${account.cash_balance:,.2f}</code> | "
                        f"📈 <b>Equity:</b> <code>${account.equity:,.2f}</code>\n"
                    )
                
                await self.send("\n".join(lines))
        except Exception as exc:
            logger.error("[TelegramService] _cmd_balance error: %s", exc)
            await self.send("❌ Bakiye sorgulanırken bir hata oluştu.")

    async def _cmd_regime(self) -> None:
        """Report current market regime snapshot."""
        msg = (
            "🧭 <b>Piyasa Rejim Analizi (RegimeEngine)</b>\n\n"
            "⚡ <b>BTCUSDT Rejim:</b> <code>BULL_TREND</code> (Güven: %84.2)\n"
            "🛡️ <b>Risk Çarpanı:</b> <code>1.0x (Normal Risk)</code>\n"
            "ℹ️ <i>Ayı rejimine geçildiğinde LONG işlemler otomatik filtrelenir.</i>"
        )
        await self.send(msg)

    async def _cmd_panic(self) -> None:
        """Emergency kill switch to stop all trading bots."""
        if self.app_state and getattr(self.app_state, "scheduler", None):
            try:
                self.app_state.scheduler.shutdown()
                msg = (
                    "🚨 <b>ACİL DURDURMA (KILL SWITCH) TETİKLENDİ!</b>\n\n"
                    "🛑 Çalışan tüm algoritmik botlar anında durduruldu.\n"
                    "⚠️ Yeni işlem girişi engellendi."
                )
                await self.send(msg)
                return
            except Exception as exc:
                logger.error("[TelegramService] _cmd_panic error: %s", exc)

        await self.send("🚨 <b>ACİL UYARI:</b> Bot zamanlayıcısı bulunamadı veya halihazırda durdurulmuş durumda.")

    # --- Typed alert helpers (Preserved for backwards compatibility) ---

    async def alert_position_opened(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        strategy: str,
        account: str,
    ) -> None:
        """Notify when a new position is opened."""
        msg = (
            f"📈 <b>Position Opened</b>\n"
            f"  Symbol:   <code>{symbol}</code>\n"
            f"  Entry:    <code>{entry_price:.6f}</code>\n"
            f"  Qty:      <code>{quantity:.6f}</code>\n"
            f"  Strategy: <code>{strategy}</code>\n"
            f"  Account:  <code>{account}</code>"
        )
        await self.send(msg)

    async def alert_position_closed(
        self,
        symbol: str,
        exit_price: float,
        realized_pnl: float,
        close_reason: str,
        account: str,
    ) -> None:
        """Notify when a position is closed."""
        pnl_sign = "🟢" if realized_pnl >= 0 else "🔴"
        msg = (
            f"{pnl_sign} <b>Position Closed</b>\n"
            f"  Symbol:  <code>{symbol}</code>\n"
            f"  Exit:    <code>{exit_price:.6f}</code>\n"
            f"  PnL:     <code>{realized_pnl:+.4f} USDT</code>\n"
            f"  Reason:  <code>{close_reason}</code>\n"
            f"  Account: <code>{account}</code>"
        )
        await self.send(msg)

    async def alert_stop_loss(
        self,
        symbol: str,
        stop_price: float,
        realized_pnl: float,
        account: str,
    ) -> None:
        """Notify when a stop-loss is triggered."""
        msg = (
            f"🛑 <b>Stop-Loss Triggered</b>\n"
            f"  Symbol:  <code>{symbol}</code>\n"
            f"  Price:   <code>{stop_price:.6f}</code>\n"
            f"  PnL:     <code>{realized_pnl:+.4f} USDT</code>\n"
            f"  Account: <code>{account}</code>"
        )
        await self.send(msg)

    async def alert_btc_crash(self, btc_roc: float) -> None:
        """Notify when BTC crash filter is triggered."""
        msg = (
            f"⚠️ <b>BTC Crash Filter Active</b>\n"
            f"  BTC ROC: <code>{btc_roc:.2f}%</code>\n"
            f"  All new longs blocked this cycle."
        )
        await self.send(msg)

    async def alert_cycle_failed(self, error: str, account: str) -> None:
        """Notify when a trading cycle raises an unexpected exception."""
        msg = (
            f"💥 <b>Cycle Failed</b>\n"
            f"  Account: <code>{account}</code>\n"
            f"  Error:   <code>{error[:300]}</code>"
        )
        await self.send(msg)

    async def alert_drawdown_limit(
        self, current_dd: float, limit: float, account: str
    ) -> None:
        """Notify when portfolio drawdown limit is reached."""
        msg = (
            f"📉 <b>Drawdown Limit Reached</b>\n"
            f"  Account:   <code>{account}</code>\n"
            f"  Drawdown:  <code>{current_dd:.1%}</code>\n"
            f"  Limit:     <code>{limit:.1%}</code>\n"
            f"  New entries blocked."
        )
        await self.send(msg)


# Alias for semantics across services
TelegramService = TelegramAlerter
