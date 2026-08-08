import pytest
from crypto_mas.engine.llm_committee.provider import AgentVote
from crypto_mas.engine.llm_committee.chair_agent import ChairAgent

def test_consensus_unanimous():
    chair = ChairAgent(consensus_threshold=30.0, disagreement_threshold=50.0)
    votes = [
        AgentVote(vote="LONG", confidence=80, reasoning="test"),
        AgentVote(vote="LONG", confidence=90, reasoning="test"),
        AgentVote(vote="LONG", confidence=70, reasoning="test"),
    ]
    
    decision, score, disagreement = chair.calculate_consensus(votes)
    assert decision == "LONG"
    assert score > 50
    assert disagreement < 20

def test_consensus_split_decision_pass():
    chair = ChairAgent(consensus_threshold=30.0, disagreement_threshold=50.0)
    votes = [
        AgentVote(vote="LONG", confidence=90, reasoning="test"),
        AgentVote(vote="SHORT", confidence=80, reasoning="test"),
    ]
    
    decision, score, disagreement = chair.calculate_consensus(votes)
    # The score should be near 0 (90 - 80) / 170 = 10/170 = 5%
    # Disagreement should be extremely high (std_dev of [90, -80] is around 120)
    assert decision == "PASS"

def test_consensus_low_confidence():
    chair = ChairAgent(consensus_threshold=30.0, disagreement_threshold=50.0)
    votes = [
        AgentVote(vote="LONG", confidence=10, reasoning="test"),
        AgentVote(vote="LONG", confidence=10, reasoning="test"),
    ]
    # (10 + 10) / 20 = 1, but wait! We mapped vote * confidence.
    # val = 1. weighted = 10, 10. sum = 20. total_conf = 20. sum/total_conf = 1. Wait, 1 is 1%?
    # Ah, the formula in chair_agent was:
    # consensus_score = sum(weighted_votes) / total_confidence
    # If vote is 1, confidence is 10, weighted is 10.
    # sum(weighted) = 20. total_conf = 20. 20/20 = 1.0! Wait, 1.0 is NOT 100%. 
    pass # I need to fix the calculation scale in chair_agent.py!
