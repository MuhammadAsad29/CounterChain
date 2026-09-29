from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CounterfactualVerdict(str, Enum):
    PREVENTED = "PREVENTED"
    PARTIALLY_MITIGATED = "PARTIALLY_MITIGATED"
    VULNERABILITY_PERSISTS = "VULNERABILITY_PERSISTS"
    SHIFTED_ATTACK_VECTOR = "SHIFTED_ATTACK_VECTOR"
    INCONCLUSIVE = "INCONCLUSIVE"

class CounterfactualResponse(BaseModel):
    """Structured Pydantic model for CounterChain counterfactual analysis."""
    verdict: CounterfactualVerdict = Field(
        ...,
        description="Final security verdict: PREVENTED, PARTIALLY_MITIGATED, VULNERABILITY_PERSISTS, SHIFTED_ATTACK_VECTOR, or INCONCLUSIVE"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 (lowest) to 1.0 (highest)"
    )
    executive_summary: str = Field(
        ...,
        description="High-level 2-3 sentence executive summary of the counterfactual evaluation"
    )
    divergence_point: str = Field(
        ...,
        description="The exact step in the transaction trace where the proposed patch intervenes and causes execution to diverge"
    )
    causal_reasoning_steps: List[str] = Field(
        default_factory=lambda: [
            "1. Baseline transaction trace inspected against vulnerability preconditions.",
            "2. Counterfactual security intervention injected into state execution path.",
            "3. Transaction state divergence and invariant preservation evaluated."
        ],
        description="Step-by-step causal reasoning chain analyzing state transitions and invariants"
    )
    residual_risks: List[str] = Field(
        default_factory=list,
        description="Residual risks, potential bypasses, gas overheads, or alternative attack vectors remaining after the patch"
    )
    recommended_code_patch: str = Field(
        ...,
        description="Solidity or pseudocode diff/snippet illustrating the correct implementation of the intervention"
    )
    source_citations: List[str] = Field(
        default_factory=list,
        description="List of cited post-mortem excerpts or sections"
    )
