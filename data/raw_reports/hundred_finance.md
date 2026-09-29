# Exploit Post-Mortem: Hundred Finance ERC-677 Reentrancy ($7.4M)

## Incident Overview
- **Protocol**: Hundred Finance (Compound v2 Fork on Optimism)
- **Loss Amount**: ~$7.4 Million
- **Incident Date**: April 15, 2023
- **Network**: Optimism (L2)
- **Vulnerability Category**: ERC-677 / ERC-777 Transfer Hook Reentrancy
- **Official Sources**: DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20230415-HundredFinance`), PeckShield Alert, Rekt.news

---

## Background & Architecture
Hundred Finance is a decentralized lending protocol forked from Compound v2 and deployed across multiple EVM chains (Optimism, Arbitrum, Fantom). 

Compound v2 was originally designed for vanilla ERC-20 tokens that do not implement fallback transfer hooks. When Hundred Finance deployed on Optimism, it listed `sUSD`, which implemented an ERC-677 token standard with a `transferAndCall` / hook mechanism.

---

## Vulnerable Smart Contract Logic
In Compound v2 forks, collateral redemption is handled in `CErc20.sol`:

```solidity
// Vulnerable CErc20.sol redeemFresh snippet
function redeemFresh(address payable redeemer, uint redeemTokensIn, uint redeemAmountIn) internal {
    ...
    // 1. Calculate exchange rate and amount
    // 2. Transfer underlying tokens to redeemer (External transfer that invokes hook)
    doTransferOut(redeemer, redeemAmount);

    // 3. Update internal cToken balance AFTER external transfer
    accountTokens[redeemer] = accountTokens[redeemer] - redeemTokensIn;
    totalSupply = totalSupply - redeemTokensIn;
    ...
}
```

### The Root Cause: Incompatibility with Token Transfer Hooks
Because `doTransferOut` triggered the ERC-677 token's callback hook on the recipient contract before reducing `accountTokens[redeemer]`, the attacker hijacked the execution thread while their collateral balance was still recorded as fully supplied.

---

## Step-by-Step Attack Vector
1. **Supply Initial Collateral**: Attacker supplied `sUSD` to mint `hsUSD`.
2. **Borrow Liquid Assets**: Attacker borrowed other available assets against the `hsUSD` collateral.
3. **Trigger Redemption with Transfer Hook**:
   - Attacker invoked `redeem()` on `hsUSD`.
   - The contract transferred underlying `sUSD` out via `doTransferOut()`.
4. **Hook Reentrancy**:
   - The token callback invoked the attacker contract's fallback.
   - Inside the callback, `accountTokens[attacker]` was still non-zero.
   - The attacker invoked `borrow()` again to extract additional assets, or manipulated the internal exchange rate.
5. **Drain Protocol**: The attacker repeated this loop to extract over $7.4M in WBTC, WETH, and DAI.

---

## Official Remediation
1. **Apply Checks-Effects-Interactions (CEI)**: Update `accountTokens` and `totalSupply` before calling `doTransferOut`.
2. **Non-Reentrant Guards**: Place global non-reentrant mutex locks across both `redeem`, `borrow`, and `liquidate`.
3. **Token Compatibility Whitelist**: Disallow listing tokens with hooks (ERC-777, ERC-677, ERC-1363) in Compound v2 forks.

---

## Key Counterfactual Invariant
- **Invariant**: *Token redemption and state accounting updates must strictly finalize prior to external asset transfers to prevent hook reentrancy.*
- **Counterfactual Hypothesis**: *If Hundred Finance had updated `accountTokens` before initiating `doTransferOut` (Checks-Effects-Interactions), the reentrant call would have seen zero collateral, preventing the $7.4M exploit.*
