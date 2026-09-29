from typing import List, Dict, Any

BENCHMARK_CASES: List[Dict[str, Any]] = [
    {
        "id": "BENCH-01",
        "protocol": "Euler Finance",
        "exploit_loss": "$197 Million",
        "query": "Would the $197M Euler Finance exploit have succeeded if donateToReserves had enforced checkLiquidity(account) on the donor account?",
        "ground_truth_verdict": "PREVENTED",
        "ground_truth_rationale": "Enforcing checkLiquidity(account) inside donateToReserves would cause the attacker's donation of 100M eDAI to immediately revert because the account held massive borrowed debt (200M dDAI) and would violate the solvency threshold.",
        "key_terms": ["donateToReserves", "checkLiquidity", "eDAI", "dDAI", "liquidation discount"]
    },
    {
        "id": "BENCH-02",
        "protocol": "Curve Finance / Vyper",
        "exploit_loss": "$73.5 Million",
        "query": "Would the Curve Finance pools (alETH, msETH, pETH) have been drained if the pools had been compiled with Vyper 0.3.1 where storage slot allocation for reentrancy locks was fixed?",
        "ground_truth_verdict": "PREVENTED",
        "ground_truth_rationale": "In Vyper 0.3.1+, functions sharing the @nonreentrant('lock') key use the identical global contract storage slot. During the raw_call ETH transfer in remove_liquidity, the attacker's reentrant callback to add_liquidity would encounter an active mutex lock and revert.",
        "key_terms": ["nonreentrant", "remove_liquidity", "add_liquidity", "raw_call", "storage slot"]
    },
    {
        "id": "BENCH-03",
        "protocol": "Cream Finance",
        "exploit_loss": "$130 Million",
        "query": "Would Cream Finance have prevented the $130M exploit if it derived collateral valuation from a 30-minute Chainlink TWAP oracle instead of the spot getPricePerShare() of the Yearn vault?",
        "ground_truth_verdict": "PREVENTED",
        "ground_truth_rationale": "The exploit relied on an instantaneous single-block donation to the Yearn vault to double getPricePerShare(). A decentralized TWAP oracle or Chainlink feed ignores intra-block spot balance spikes, meaning the collateral value would remain unchanged and prevent the excessive borrowing.",
        "key_terms": ["getPricePerShare", "TWAP", "Chainlink", "spot price", "yUSD"]
    },
    {
        "id": "BENCH-04",
        "protocol": "Platypus Finance",
        "exploit_loss": "$8.5 Million",
        "query": "Would Platypus Finance have been exploited if emergencyWithdraw asserted that the user's borrowed USP debt balance is zero?",
        "ground_truth_verdict": "PREVENTED",
        "ground_truth_rationale": "The exploit succeeded because emergencyWithdraw allowed 100% collateral extraction while 41.7M USP debt was outstanding. Requiring debtOf(msg.sender) == 0 causes the transaction to revert immediately.",
        "key_terms": ["emergencyWithdraw", "debtOf", "USP", "MasterPlatypusV4", "isSolvent"]
    },
    {
        "id": "BENCH-05",
        "protocol": "Cream Finance (Control Case - Ineffective Patch)",
        "exploit_loss": "$130 Million",
        "query": "What if Cream Finance had capped single flash loans to $50M per transaction without changing the spot oracle pricing mechanism?",
        "ground_truth_verdict": "VULNERABILITY_PERSISTS",
        "ground_truth_rationale": "Capping flash loan size per transaction does not fix the root vulnerability: the spot price calculation remains manipulable. The attacker could either execute multiple sequential transactions across blocks or pool capital from multiple sources to achieve the same result.",
        "key_terms": ["flash loan cap", "spot oracle", "root cause", "VULNERABILITY_PERSISTS"]
    },
    {
        "id": "BENCH-06",
        "protocol": "GMX V1",
        "exploit_loss": "$42 Million",
        "query": "Would the $42M GMX V1 exploit have been prevented if timelock.disableLeverage() was invoked before sending ETH profit to the user in executeDecreaseOrder (Checks-Effects-Interactions)?",
        "ground_truth_verdict": "PREVENTED",
        "ground_truth_rationale": "The exploit succeeded because ETH profit was transferred to the user contract before timelock.disableLeverage() disabled direct Vault interactions. Invoking disableLeverage() before external transfer blocks the receiver contract's reentrant attempt to open a direct Vault short position, stopping the GLP price manipulation.",
        "key_terms": ["disableLeverage", "executeDecreaseOrder", "PositionManager", "GLP", "reentrancy"]
    }
]
