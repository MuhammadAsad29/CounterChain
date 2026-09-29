# Exploit Post-Mortem: Beanstalk Farms Flash Loan Governance Exploit ($182M)

## Incident Overview
- **Protocol**: Beanstalk Farms (Decentralized Credit/Stablecoin Protocol)
- **Loss Amount**: ~$182 Million
- **Incident Date**: April 17, 2022
- **Network**: Ethereum Mainnet
- **Vulnerability Category**: Flash Loan Governance Attack / Missing Voting Timelock
- **Official Sources**: Trail of Bits Security Case Study, Rekt.news (Beanstalk Farms Exploit), DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20220417-Beanstalk`)

---

## Background & Architecture
Beanstalk is a credit-based algorithmic stablecoin protocol. Users deposited liquidity into Beanstalk's "Silo" to earn "Stalk" (governance voting power) and "Seeds".

Beanstalk governed protocol upgrades and emergency actions through Beanstalk Improvement Proposals (BIPs). Under BIP emergency rules, if a proposal achieved a supermajority of Stalk voting power (>66%), it could be executed immediately without waiting for the standard 24-hour voting delay.

---

## Vulnerable Smart Contract Logic
In Beanstalk's `GovernanceFacet.sol`:

```solidity
// Vulnerable emergency governance execution
function emergencyCommit(uint32 bipId) external {
    Proposal storage p = proposals[bipId];
    require(block.timestamp >= p.timestamp, "Voting not started");
    
    // Check if proposal has reached 66.6% of current Stalk voting power
    require(p.roots > (totalRoots() * 2) / 3, "Not enough voting power");
    
    // Execute proposed arbitrary code via delegatecall
    (bool success, ) = p.executionAddress.delegatecall(p.data);
    require(success, "Execution failed");
}
```

### The Root Cause: Flash Loan Snapshotting & Zero Timelock
Beanstalk calculated voting power (`totalRoots()`) dynamically using current Stalk deposits within the active block. It did not take a snapshot of voting power at a prior block number (such as `block.number - 1` or a historical snapshot).

Therefore, an attacker could borrow a billion dollars in a flash loan, deposit the funds into the Silo to instantly gain >70% of all voting Stalk, vote in favor of a malicious proposal (BIP-18) that drained the protocol reserves to a target wallet, trigger `emergencyCommit()`, withdraw their deposits, and repay the flash loan — all within a single Ethereum transaction!

---

## Step-by-Step Attack Vector
1. **Flash Loan Ingestion**: Attacker flash-borrowed ~$1 Billion: 350M DAI, 500M USDC, 150M USDT from Aave, and 32M BEAN from Uniswap v3.
2. **Convert to Curve LP**: Swapped borrowed stablecoins for Curve Bean:3CRV pool LP tokens.
3. **Deposit into Silo**: Deposited the Curve LP tokens into Beanstalk's Silo.
4. **Acquire Instant Supermajority**: This gave the attacker 79% of all active Stalk voting power.
5. **Vote & Execute BIP-18**:
   - The attacker voted for BIP-18 (a proposal crafted by the attacker that transferred all protocol assets to the attacker).
   - Called `emergencyCommit(18)`. The contract saw 79% voting power and executed the arbitrary drain code.
6. **Drain Assets**: $182M in ETH, BEAN, and 3CRV were transferred to the attacker.
7. **Withdraw & Repay**: Attacker withdrew their LP tokens from the Silo, repaid the flash loans, and kept over $76M in clean profit.

---

## Official Remediation
1. **Historical Snapshot Voting**: Standardize on OpenZeppelin Governor or Compound Bravo, taking voting power snapshots at `block.number - 1` or earlier, rendering intra-block flash loan voting mathematically impossible.
2. **Mandatory Execution Timelock**: Disallow same-block or emergency execution of treasury withdrawals without at least a 24-hour minimum timelock delay.

---

## Key Counterfactual Invariant
- **Invariant**: *Governance voting power must be derived from a historical block snapshot prior to proposal submission, and must never recognize same-block deposit changes.*
- **Counterfactual Hypothesis**: *If Beanstalk had derived voting power from a historical block snapshot (e.g. `getPastVotes(account, proposalSnapshot)`), the flash loan deposit in the same block would have yielded 0 voting power for BIP-18, completely preventing the $182M drain.*
