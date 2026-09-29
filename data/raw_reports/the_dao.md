# Exploit Post-Mortem: The DAO Hack ($60M)

## Incident Overview
- **Protocol**: The DAO
- **Loss Amount**: ~$60 Million (3.6M ETH)
- **Incident Date**: June 17, 2016
- **Network**: Ethereum
- **Vulnerability Category**: Recursive Reentrancy / State Update Ordering Violation
- **Official Sources**: ConsenSys Diligence Historical Archive, Ethereum Foundation Incident Write-up, Phil Daian Analysis

---

## Background & Architecture
The DAO was an investor-directed venture capital decentralized autonomous organization on Ethereum. Users deposited ETH in exchange for DAO voting tokens. 

A feature called `splitDAO` allowed dissenting token holders to split from the parent DAO and create a "Child DAO" to retrieve their pro-rata share of deposited ETH.

---

## Vulnerable Smart Contract Logic
In `DAO.sol`, the split logic was handled in `splitDAO()`:

```solidity
// Vulnerable DAO.sol split logic
function splitDAO(uint _proposalID, address _newCurator) returns (bool) {
    ...
    // 1. Calculate user balance and reward
    uint fundsToBeMoved = (balances[msg.sender] * p.amount) / totalEther;
    
    // 2. Send Ether to user contract BEFORE updating balance state (VULNERABILITY!)
    msg.sender.call.value(fundsToBeMoved)();

    // 3. Update user balance AFTER external call
    balances[msg.sender] = 0;
    paidOut[msg.sender] += fundsToBeMoved;
    totalEther -= fundsToBeMoved;
    ...
}
```

### The Root Cause: Checks-Effects-Interactions Violation
The smart contract transferred Ether to `msg.sender` before resetting `balances[msg.sender] = 0`.
When `msg.sender.call.value()` was executed, control transferred to the attacker's fallback function. Inside the fallback function, `balances[msg.sender]` was still non-zero. The attacker recursively invoked `splitDAO()`, repeatedly withdrawing Ether until the contract call stack or gas limit was reached.

---

## Step-by-Step Attack Vector
1. **Submit Split Proposal**: Attacker submitted a proposal to split from The DAO.
2. **Execute Initial Split**: Attacker called `splitDAO()`.
3. **External Transfer Trigger**: The DAO contract transferred ETH to the attacker's contract.
4. **Fallback Reentrant Loop**:
   - The attacker's contract received the ETH in its fallback function.
   - Fallback immediately re-invoked `splitDAO()`.
   - The DAO contract checked `balances[msg.sender]`, which was still full balance because line `balances[msg.sender] = 0` was never reached.
   - Another ETH transfer was initiated.
5. **Repeated Extraction**: This recursion repeated 20-30 times per transaction, extracting over 3.6M ETH into the attacker's Dark DAO.

---

## Official Remediation & Code Diff
This incident established the canonical **Checks-Effects-Interactions (CEI)** pattern and the OpenZeppelin `ReentrancyGuard`:

```diff
function splitDAO(uint _proposalID, address _newCurator) returns (bool) {
    uint fundsToBeMoved = (balances[msg.sender] * p.amount) / totalEther;

+   // 1. EFFECT: Update internal state FIRST
+   balances[msg.sender] = 0;
+   paidOut[msg.sender] += fundsToBeMoved;
+   totalEther -= fundsToBeMoved;

-   // 2. INTERACTION: External transfer AFTER state update
    msg.sender.call.value(fundsToBeMoved)();
-   balances[msg.sender] = 0;
}
```

---

## Key Counterfactual Invariant
- **Invariant**: *All internal accounting state modifications must be finalized before making external contract calls or value transfers (Checks-Effects-Interactions).*
- **Counterfactual Hypothesis**: *If `balances[msg.sender] = 0` had been executed before the `call.value()` transfer (or protected by a nonReentrant mutex), the reentrant call would have seen a zero balance and transferred 0 ETH, completely preventing the $60M drain.*
