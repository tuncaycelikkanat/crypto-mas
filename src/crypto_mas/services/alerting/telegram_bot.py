"""
telegram_bot.py — Lightweight Telegram alerter using httpx.

Sends notifications to a Telegram chat via Bot API.
No external Telegram library required — uses httpx (already a project dependency).

Configuration (via .env):
    TELEGRAM_BOT_TOKEN=<your bot token>
    TELEGRAM_CHAT_ID=<your chat id>
"""
import logging

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramAlerter:
    """Async Telegram notification sender.

    Inject an instance into services that should emit alerts.
    All methods are safe to call with missing credentials — they log a warning
    and return silently so production code is never disrupted by alerting failures.
    """

    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self.token = token
        self.chat_id = chat_id
        self._enabled = bool(token and chat_id)
        if not self._enabled:
            logger.info(
                "[TelegramAlerter] Disabled — set TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID to enable."
            )

    async def send(self, message: str) -> None:
        """Send a plain-text message to the configured Telegram chat."""
        if not self._enabled:
            return
        url = TELEGRAM_API_BASE.format(token=self.token)
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

    # --- Typed alert helpers ---

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
