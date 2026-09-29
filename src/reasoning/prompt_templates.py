from typing import List, Dict, Any

SYSTEM_PROMPT = """You are CounterChain, a Principal DeFi Smart Contract Security Auditor and Formal Verification Specialist.
Your objective is to perform rigorous Counterfactual Security Analysis on decentralized finance (DeFi) exploits based on verified post-mortem documentation from DeFiHackLabs and Rekt.news.

When given a counterfactual query (e.g. "What if intervention X had been applied?"):
1. Base your causal reasoning STRICTLY on the provided post-mortem excerpts (root cause, contract mechanics, attack transaction trace).
2. Trace the exact point of divergence where the proposed patch alters the smart contract's state machine.
3. Determine whether the attack transaction would:
   - REVERT (e.g. require assertion failure, mutex lock revert, health factor check revert) -> PREVENTED
   - REDUCE DAMAGE or SLOW DOWN -> PARTIALLY_MITIGATED
   - CONTINUE UNIMPEDED (the patch touches an irrelevant function or doesn't close the root cause) -> VULNERABILITY_PERSISTS
   - INTRODUCE OR SHIFT TO A NEW VULNERABILITY -> SHIFTED_ATTACK_VECTOR
   - LACK SUFFICIENT EVIDENCE TO PROVE -> INCONCLUSIVE
4. Evaluate residual risks (e.g. front-running, gas griefing, alternative drain vectors, reentrancy via another path).
5. Provide a clean Solidity code patch demonstrating the fix.

You MUST respond strictly with a valid JSON object matching the requested schema. No conversational filler or markdown wrapping outside the JSON.
"""

def build_counterfactual_prompt(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    protocol_hint: str = ""
) -> str:
    """Construct the grounding prompt with retrieved context chunks."""
    context_str = ""
    for i, c in enumerate(retrieved_chunks, 1):
        context_str += f"""
--- EXCERPT {i} [Protocol: {c.get('protocol', 'Unknown')} | Section: {c.get('section', 'General')}] ---
{c.get('text', '')}
"""

    prompt = f"""COUNTERFACTUAL SECURITY ANALYSIS REQUEST

[PROPOSED HYPOTHETICAL / COUNTERFACTUAL QUERY]
{query}

{f'[TARGET PROTOCOL]: {protocol_hint}' if protocol_hint else ''}

[VERIFIED POST-MORTEM GROUNDING EVIDENCE]
{context_str}

[TASK INSTRUCTIONS]
Carefully analyze the counterfactual hypothesis against the real attack trace provided above.
Return a single JSON object with EXACTLY the following keys:
{{
  "verdict": "PREVENTED" | "PARTIALLY_MITIGATED" | "VULNERABILITY_PERSISTS" | "SHIFTED_ATTACK_VECTOR" | "INCONCLUSIVE",
  "confidence_score": <float between 0.0 and 1.0>,
  "executive_summary": "<2-3 sentence overview of the counterfactual finding>",
  "divergence_point": "<exact step/function in the attack transaction where execution diverges>",
  "causal_reasoning_steps": [
    "<Step 1: State of contract prior to intervention>",
    "<Step 2: Execution path when attacker triggers the modified function>",
    "<Step 3: Invariant check evaluation (revert condition or state modification)>",
    "<Step 4: Ultimate consequence on attacker's profit/drain capability>"
  ],
  "residual_risks": [
    "<Potential bypass or unaddressed edge case 1>",
    "<Potential bypass or unaddressed edge case 2>"
  ],
  "recommended_code_patch": "<Solidity diff or code snippet implementing the fix>",
  "source_citations": [
    "<Citation to post-mortem section or specific contract function>"
  ]
}}
"""
    return prompt
