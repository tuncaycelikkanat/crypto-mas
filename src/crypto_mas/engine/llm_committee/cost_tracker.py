import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from crypto_mas.domain.models.llm_audit_log import LLMAuditLog
from crypto_mas.services.alerting.telegram_bot import TelegramAlerter

class CostTracker:
    def __init__(self, daily_cap_usd: float = 20.0):
        self.daily_cap_usd = daily_cap_usd
        self._alerter = TelegramAlerter.get_instance()

    async def check_daily_limit(self, db_session: Session) -> bool:
        """
        Returns True if the system is allowed to use LLM. Returns False if cap is exceeded.
        """
        today = datetime.datetime.now(datetime.timezone.utc).date()
        
        stmt = select(func.sum(LLMAuditLog.cost_usd)).where(
            func.date(LLMAuditLog.created_at) == today
        )
        total_cost = db_session.execute(stmt).scalar() or 0.0
        
        if total_cost >= self.daily_cap_usd:
            if self._alerter:
                await self._alerter.send(
                    f"🚨 *LLM LİMİTİ AŞILDI*\n\nGünlük limit (${self.daily_cap_usd}) doldu. Güncel harcama: ${total_cost:.2f}\nLLM Komitesi yarına kadar devre dışı (Fallback modunda çalışacak)."
                )
            return False
            
        if total_cost >= self.daily_cap_usd * 0.8:
            if self._alerter:
                await self._alerter.send(
                    f"⚠️ *LLM LİMİT UYARISI*\n\nGünlük limitin %80'ine ulaşıldı. Güncel harcama: ${total_cost:.2f} / ${self.daily_cap_usd}"
                )
            
        return True
