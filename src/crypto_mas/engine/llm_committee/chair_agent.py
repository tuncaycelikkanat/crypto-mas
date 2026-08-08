import statistics
from crypto_mas.engine.llm_committee.provider import AgentVote

class ChairAgent:
    def __init__(self, consensus_threshold: float = 30.0, disagreement_threshold: float = 50.0):
        self.consensus_threshold = consensus_threshold
        self.disagreement_threshold = disagreement_threshold

    def calculate_consensus(self, votes: list[AgentVote]) -> tuple[str, float, float]:
        """
        Calculates the confidence-weighted consensus score and disagreement.
        Returns: (final_decision, consensus_score, disagreement)
        """
        if not votes:
            return "PASS", 0.0, 0.0
            
        vote_values = []
        confidences = []
        
        for v in votes:
            val = 0
            if v.vote.upper() == "LONG":
                val = 1
            elif v.vote.upper() == "SHORT":
                val = -1
            
            vote_values.append(val)
            confidences.append(v.confidence)
            
        total_confidence = sum(confidences)
        if total_confidence == 0:
            return "PASS", 0.0, 0.0
            
        # vote_value (-1, 0, 1) * confidence (0-100)
        weighted_votes = [vote_values[i] * confidences[i] for i in range(len(votes))]
        
        # Scale to -100 to 100
        consensus_score = (sum(weighted_votes) / total_confidence) * 100.0
        
        if len(weighted_votes) > 1:
            disagreement = statistics.stdev(weighted_votes)
        else:
            disagreement = 0.0
            
        if abs(consensus_score) < self.consensus_threshold or disagreement > self.disagreement_threshold:
            final_decision = "PASS"
        elif consensus_score >= self.consensus_threshold:
            final_decision = "LONG"
        else:
            final_decision = "SHORT"
            
        return final_decision, consensus_score, disagreement
