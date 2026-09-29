# Exploit Post-Mortem: Platypus Finance ($8.5M Exploit)

## Incident Overview
- **Protocol**: Platypus Finance (USP Stablecoin MasterChef)
- **Loss Amount**: ~$8.5 Million
- **Incident Date**: February 16, 2023
- **Network**: Avalanche (C-Chain)
- **Vulnerability Category**: Flawed Logic / Omitted Solvency Invariant in Emergency Withdraw
- **Official Sources**: Omniscia Security Audit Post-Mortem, DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20230216-Platypus`), Rekt.news

---

## Background & Architecture
Platypus Finance is a single-sided AMM for stablecoins on Avalanche. It introduced a native stablecoin named `USP` that users could mint by borrowing against their staked pool liquidity tokens (LP tokens) in the `MasterPlatypusV4` contract.

When a user deposits collateral and mints USP, their account holds both an LP collateral balance and a USP debt liability. Under normal withdrawals (`withdraw`), Platypus checked `isSolvent(user)` to ensure the user did not withdraw collateral backing active USP debt.

---

## Vulnerable Smart Contract Logic
In `MasterPlatypusV4.sol`, the team implemented an emergency escape hatch function: `emergencyWithdraw()`:

```solidity
// Vulnerable MasterPlatypusV4.sol snippet
function emergencyWithdraw(uint256 _pid) external nonReentrant {
    PoolInfo storage pool = poolInfo[_pid];
    UserPosition storage user = userPositions[_pid][msg.sender];
    
    uint256 amount = user.amount;
    user.amount = 0;
    user.rewardDebt = 0;

    // TRANSFER BACK ALL STAKED LP COLLATERAL
    pool.lpToken.safeTransfer(address(msg.sender), amount);
    emit EmergencyWithdraw(msg.sender, _pid, amount);

    // CRITICAL FLAW: isSolvent() WAS COMPLETELY OMITTED!
    // The contract checked neither USP debt nor health factor!
}
```

### The Root Cause
Developers copied a standard MasterChef `emergencyWithdraw()` pattern, which is intended to let users recover deposits if rewards break. However, because Platypus added a **lending/borrowing layer (USP minting)** on top of MasterChef, an emergency withdrawal must NEVER allow withdrawing collateral while debt is still outstanding.

Because `emergencyWithdraw` failed to check whether the user had borrowed USP against the collateral, any user could borrow USP, invoke `emergencyWithdraw()`, take back 100% of their collateral, and leave the protocol with unbacked USP debt.

---

## Step-by-Step Attack Vector
1. **Flash Loan Ingestion**: Attacker flash-borrowed 44M USDC from Aave v3 on Avalanche.
2. **Deposit Collateral**: Attacker deposited 44M USDC into Platypus's USDC pool, receiving LP tokens.
3. **Mint USP Stablecoin**: Attacker deposited LP tokens into `MasterPlatypusV4` and minted ~41.7M USP (a borrowed liability).
4. **Trigger `emergencyWithdraw`**:
   - Attacker called `emergencyWithdraw(pid)`.
   - The contract transferred the 44M LP tokens back to the attacker.
   - The attacker's USP debt remained unpaid in Platypus accounting, but the protocol had zero collateral left.
5. **Withdraw Original Collateral**: Attacker unstaked their 44M LP tokens back to 44M USDC.
6. **Repay Flash Loan**: Attacker repaid the 44M USDC flash loan.
7. **Cash Out Stolen USP**:
   - The attacker traded their unbacked 41.7M USP for liquid stablecoins (USDC, USDT, BUSD) across Platypus pools.
   - Attacker walked away with $8.5M in net drained assets.

---

## Official Remediation & Code Diff
Platypus patched the function by strictly verifying that the user has zero debt or remains fully solvent:

```diff
function emergencyWithdraw(uint256 _pid) external nonReentrant {
    PoolInfo storage pool = poolInfo[_pid];
    UserPosition storage user = userPositions[_pid][msg.sender];
    
+   // REMEDIATION: Enforce that user has no outstanding borrowed USP debt
+   require(platypusTreasure.debtOf(msg.sender) == 0, "Platypus: active debt outstanding");
    
    uint256 amount = user.amount;
    user.amount = 0;
    user.rewardDebt = 0;

    pool.lpToken.safeTransfer(address(msg.sender), amount);
    emit EmergencyWithdraw(msg.sender, _pid, amount);
}
```

---

## Key Counterfactual Invariant
- **Invariant**: *No account may withdraw collateral assets from a lending/staking contract if that collateral is currently pledged against an outstanding debt position.*
- **Counterfactual Hypothesis**: *If `emergencyWithdraw()` had asserted `debtOf(msg.sender) == 0`, the transaction would have immediately reverted, preventing the $8.5M theft.*
