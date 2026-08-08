import asyncio
import logging
from sqlalchemy.orm import Session
from crypto_mas.domain.models.committee_decision import CommitteeDecision
from crypto_mas.domain.models.shadow_mode_trade import ShadowModeTrade
from crypto_mas.domain.models.llm_audit_log import LLMAuditLog
from crypto_mas.engine.llm_committee.provider import LLMProvider
from crypto_mas.engine.llm_committee.agents import TechnicalAgent, SentimentAgent, RiskAgent
from crypto_mas.engine.llm_committee.chair_agent import ChairAgent
from crypto_mas.engine.llm_committee.cost_tracker import CostTracker
from crypto_mas.engine.strategy.schemas import TradingDecision

logger = logging.getLogger(__name__)

class LLMCommitteeOrchestrator:
    def __init__(self, provider: LLMProvider, cost_tracker: CostTracker):
        self.provider = provider
        self.cost_tracker = cost_tracker
        
        self.technical = TechnicalAgent(provider)
        self.sentiment = SentimentAgent(provider)
        self.risk = RiskAgent(provider)
        self.chair = ChairAgent(consensus_threshold=30.0, disagreement_threshold=50.0)

    async def evaluate_decision(self, symbol: str, context: dict, original_decision: TradingDecision, db: Session) -> TradingDecision:
        """
        Evaluates a signal using the LLM Committee.
        If fallback triggered or timeout/validation error, returns the original decision.
        """
        is_allowed = await self.cost_tracker.check_daily_limit(db)
        if not is_allowed:
            return original_decision

        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    self.technical.vote(context),
                    self.sentiment.vote(context),
                    self.risk.vote(context),
                    return_exceptions=False
                ),
                timeout=20.0
            )
            
            tech_vote, tech_meta = results[0]
            sent_vote, sent_meta = results[1]
            risk_vote, risk_meta = results[2]
            
            votes = [tech_vote, sent_vote, risk_vote]
            
            final_action_str, consensus_score, disagreement = self.chair.calculate_consensus(votes)
            
            decision_record = CommitteeDecision(
                symbol=symbol,
                market_regime=context.get("market_regime", "UNKNOWN"),
                votes={
                    "TechnicalAgent": tech_vote.model_dump(),
                    "SentimentAgent": sent_vote.model_dump(),
                    "RiskAgent": risk_vote.model_dump()
                },
                consensus_score=consensus_score,
                final_decision=final_action_str,
                source="llm_committee",
                shadow_mode=True
            )
            db.add(decision_record)
            db.flush()  # to get ID before creating shadow trade
            
            shadow_trade = ShadowModeTrade(
                committee_decision_id=decision_record.id,
                rule_based_decision=original_decision.action.value,
                regime_at_entry=context.get("market_regime", "UNKNOWN")
            )
            db.add(shadow_trade)
            db.commit()
            
            for name, vote, meta in [
                ("TechnicalAgent", tech_vote, tech_meta),
                ("SentimentAgent", sent_vote, sent_meta),
                ("RiskAgent", risk_vote, risk_meta)
            ]:
                log = LLMAuditLog(
                    symbol=symbol,
                    agent_name=name,
                    prompt=meta.get("prompt", ""),
                    response_json=vote.model_dump(),
                    model_version=meta.get("model_version", ""),
                    prompt_template_version="v1",
                    latency_ms=meta.get("latency_ms", 0),
                    cost_usd=meta.get("cost_usd", 0.0),
                    decision_id=decision_record.id
                )
                db.add(log)
                
            db.commit()
            logger.info(f"LLM Committee decided {final_action_str} for {symbol}. Score: {consensus_score:.2f}")
            
            return original_decision
            
        except Exception as e:
            logger.error(f"LLM Committee error for {symbol}: {e}")
            log = LLMAuditLog(
                symbol=symbol,
                agent_name="SYSTEM_FALLBACK",
                prompt=f"Error: {str(e)}",
                response_json={},
                model_version="fallback",
                prompt_template_version="v1",
                latency_ms=0,
                cost_usd=0.0,
                fallback_triggered=True
            )
            db.add(log)
            db.commit()
            return original_decision
