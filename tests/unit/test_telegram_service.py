"""Unit tests for TelegramService (two-way notification & command center)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from crypto_mas.services.alerting.telegram_bot import TelegramService


@pytest.mark.asyncio
async def test_telegram_disabled():
    service = TelegramService(token=None, chat_id=None)
    assert not service._enabled

    # Should silently return when disabled
    await service.send("hello")
    await service.start_polling(app_state=None)
    assert not service._is_polling


@pytest.mark.asyncio
async def test_telegram_enabled_and_auth():
    service = TelegramService(token="123:ABC", chat_id="999888")
    assert service._enabled
    assert service.chat_id == "999888"

    # Unauthorized message from different chat_id should be ignored
    with patch.object(service, "_dispatch_command", new_callable=AsyncMock) as mock_dispatch:
        await service._handle_message({"chat": {"id": "111111"}, "text": "/help"})
        mock_dispatch.assert_not_called()

    # Authorized message should dispatch
    with patch.object(service, "_dispatch_command", new_callable=AsyncMock) as mock_dispatch:
        await service._handle_message({"chat": {"id": "999888"}, "text": "/help"})
        mock_dispatch.assert_called_once_with("/help")


@pytest.mark.asyncio
async def test_telegram_cmd_help():
    service = TelegramService(token="123:ABC", chat_id="999888")
    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service._dispatch_command("/help")
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "KULLANILABİLİR KOMUTLAR" in text
        assert "/status" in text
        assert "/positions" in text
        assert "/balance" in text
        assert "/regime" in text
        assert "/panic" in text


@pytest.mark.asyncio
async def test_telegram_cmd_test():
    service = TelegramService(token="123:ABC", chat_id="999888")
    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service._dispatch_command("/test")
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "PONG!" in text
        assert "Bağlantısı Başarılı" in text


@pytest.mark.asyncio
async def test_telegram_cmd_status():
    service = TelegramService(token="123:ABC", chat_id="999888")
    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service._dispatch_command("/status")
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Sistem Durumu" in text


@pytest.mark.asyncio
async def test_telegram_cmd_regime():
    service = TelegramService(token="123:ABC", chat_id="999888")
    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service._dispatch_command("/regime")
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "Piyasa Rejim Analizi" in text


@pytest.mark.asyncio
async def test_telegram_cmd_panic():
    service = TelegramService(token="123:ABC", chat_id="999888")
    mock_scheduler = MagicMock()
    app_state = MagicMock()
    app_state.scheduler = mock_scheduler
    service.app_state = app_state

    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service._dispatch_command("/panic")
        mock_scheduler.shutdown.assert_called_once()
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "ACİL DURDURMA" in text


@pytest.mark.asyncio
async def test_telegram_alert_helpers():
    service = TelegramService(token="123:ABC", chat_id="999888")
    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service.alert_position_opened("BTCUSDT", 65000.0, 0.1, "macd", "default")
        await service.alert_position_closed("BTCUSDT", 66000.0, 100.0, "TP", "default")
        await service.alert_stop_loss("BTCUSDT", 64000.0, -100.0, "default")
        await service.alert_btc_crash(-5.5)
        await service.alert_cycle_failed("connection error", "default")
        await service.alert_drawdown_limit(0.15, 0.10, "default")

        assert mock_send.call_count == 6


@pytest.mark.asyncio
async def test_telegram_slash_optional():
    service = TelegramService(token="123:ABC", chat_id="999888")
    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service._handle_message({"chat": {"id": "999888"}, "text": "status"})
        mock_send.assert_called_once()
        assert "Sistem Durumu" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_telegram_cmd_status_with_scheduler():
    service = TelegramService(token="123:ABC", chat_id="999888")
    mock_scheduler = MagicMock()
    mock_scheduler.get_status.return_value = {"bots": [{"id": "bot1"}, {"id": "bot2"}]}
    app_state = MagicMock()
    app_state.scheduler = mock_scheduler
    service.app_state = app_state

    with patch.object(service, "send", new_callable=AsyncMock) as mock_send:
        await service._dispatch_command("status")
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "2" in text  # 2 active bots

