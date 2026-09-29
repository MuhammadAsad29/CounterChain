# Exploit Post-Mortem: Euler Finance ($197M Exploit)

## Incident Overview
- **Protocol**: Euler Finance
- **Loss Amount**: ~$197 Million (in DAI, WBTC, sETH, USDC)
- **Incident Date**: March 13, 2023
- **Network**: Ethereum Mainnet
- **Vulnerability Category**: Flawed Logic / Omitted Invariant Solvency Check (`donateToReserves`)
- **Official Sources**: Rekt.news (Euler Finance Post-Mortem), DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20230313-EulerFinance`), PeckShield Alert

---

## Background & Architecture
Euler Finance is a permissionless decentralized lending protocol on Ethereum. It introduced risk-adjusted borrowing tiers (Collateral Tier, Cross Tier, Isolated Tier) and minted interest-bearing eTokens (representing deposited assets) and dTokens (representing debt liability).

A core design principle of Euler was that an account cannot enter a state of liquidation unless its risk-adjusted collateral value falls below its borrowed liabilities. The protocol maintained a health score via `checkLiquidity(address account)` in `RiskManager.sol`.

---

## Vulnerable Smart Contract Logic
In Euler's `EToken.sol`, the protocol implemented a donation function `donateToReserves(uint subAccountId, uint amount)` allowing lenders to donate their underlying eToken assets directly to the protocol reserve pool:

```solidity
// Vulnerable EToken.sol snippet
function donateToReserves(uint subAccountId, uint amount) external nonReentrant {
    (address underlying, AssetStorage storage assetStorage, address proxyAddr, uint msgSenderSubAccountId) = unpackTrailingParams();
    address account = getSubAccount(msg.sender, subAccountId);
    
    updateAverageLiquidity(account);
    emit RequestDonate(account, amount);

    // DEDUCT ETOKEN BALANCE FROM DONOR ACCOUNT
    assetStorage.users[account].balance -= amount;
    assetStorage.reserveBalance += amount;

    // CRITICAL FLAW: checkLiquidity(account) WAS NEVER CALLED HERE!
}
```

### The Root Cause
Unlike normal withdrawals (`withdraw`) or transfers (`transfer`), `donateToReserves()` intentionally allowed users to reduce their collateral balance without verifying whether the account had outstanding debt!

While donating when you have zero debt is harmless, donating when you hold massive leveraged debt allows a user to artificially push their own account into deep insolvency without the protocol reverting.

---

## Step-by-Step Attack Vector
1. **Flash Loan Ingestion**: Attacker flash-borrowed 30M DAI from Aave v2.
2. **Deposit & Collateralization**: Attacker deposited 20M DAI into Euler, receiving 19.5M eDAI.
3. **Recursive Minting**: Attacker minted 195M eDAI and took on 200M dDAI of debt using Euler's 10x leverage mechanism.
4. **The Donation Trigger**: Attacker called `donateToReserves(subAccountId, 100M eDAI)`.
   - The attacker burned 100M of their eDAI collateral.
   - Euler accepted the donation because `checkLiquidity()` was omitted.
   - The attacker's account now held ~95M eDAI collateral against ~200M dDAI debt: completely insolvent.
5. **Self-Liquidation Arbitrage**:
   - Because the account was underwater, Euler's liquidation engine activated.
   - The liquidation contract provided a liquidation discount (bonus collateral) to the liquidator.
   - The attacker, operating a second contract, liquidated their own first account, capturing the bonus collateral at a steep discount.
6. **Repayment & Drain**: Attacker repaid the 30M DAI flash loan and walked away with tens of millions in net profit.

---

## Official Remediation & Code Diff
Euler patched the vulnerability by enforcing a strict health check on the donor account within `donateToReserves`:

```diff
function donateToReserves(uint subAccountId, uint amount) external nonReentrant {
    (address underlying, AssetStorage storage assetStorage, address proxyAddr, uint msgSenderSubAccountId) = unpackTrailingParams();
    address account = getSubAccount(msg.sender, subAccountId);
    
    updateAverageLiquidity(account);
    emit RequestDonate(account, amount);

    assetStorage.users[account].balance -= amount;
    assetStorage.reserveBalance += amount;

+   // REMEDIATION: Enforce liquidity check on the donor account
+   checkLiquidity(account);
}
```

---

## Key Counterfactual Invariant
- **Invariant**: *A user account with outstanding debt must never decrease its collateral ratio below the liquidation threshold within any transaction.*
- **Counterfactual Hypothesis**: *If `checkLiquidity(account)` had been enforced inside `donateToReserves`, the attacker's donation would have immediately reverted due to insolvency, preventing the $197M exploit entirely.*
