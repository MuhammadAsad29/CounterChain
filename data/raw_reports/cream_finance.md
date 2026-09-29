# Exploit Post-Mortem: Cream Finance ($130M Exploit)

## Incident Overview
- **Protocol**: Cream Finance (Compound v2 Fork)
- **Loss Amount**: ~$130 Million
- **Incident Date**: October 27, 2021
- **Network**: Ethereum Mainnet
- **Vulnerability Category**: Flash Loan Price Oracle Manipulation / Illiquid Collateral Valuation
- **Official Sources**: PeckShield Incident Report, Rekt.news (Cream Finance Exploit Post-Mortem), DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20211027-CreamFinance`)

---

## Background & Architecture
Cream Finance is a multi-chain decentralized lending protocol based on Compound v2. Lenders supply supported collateral tokens to earn yield and borrow other tokens up to a loan-to-value (LTV) limit.

Cream listed `crvUSD` / `yUSD` vault LP tokens as an accepted collateral asset. To determine the price of `crvUSD`, Cream used Yearn's vault share price calculation:
$$\text{Price} = \frac{\text{Total Assets}}{\text{Total Supply}}$$

---

## Vulnerable Smart Contract Logic
In Cream's Compound Price Oracle adapter for Yearn LP tokens:

```solidity
// Vulnerable Price Oracle calculation
function getUnderlyingPrice(CToken cToken) external view returns (uint) {
    if (cToken == cyUSD) {
        // Vault share price derived directly from Yearn pool balance
        uint pricePerShare = yVault(underlying).getPricePerShare();
        return pricePerShare * getCurveVirtualPrice();
    }
    ...
}
```

### The Root Cause: Spot Oracle Susceptibility & Direct Donation
`getPricePerShare()` relies on `totalAssets() / totalSupply()`. An attacker can manipulate `totalAssets()` instantaneously by directly transferring tokens into the Yearn vault contract without minting new shares. Because Cream evaluated collateral value using this instant spot share price without a Time-Weighted Average Price (TWAP) or liquidity depth bounds, the collateral valuation could be inflated to extreme levels within a single atomic transaction.

---

## Step-by-Step Attack Vector
1. **Flash Loan Ingestion**: Attacker flash-loaned 500M DAI from MakerDAO and 2B DAI from Aave.
2. **Deposit into Yearn Vault**: Attacker minted a substantial amount of `yUSD` vault shares.
3. **Double Collateral Minting**: Attacker supplied `yUSD` to Cream to mint `cyUSD`.
4. **Spot Price Pumping via Donation**:
   - Attacker transferred a massive amount of `yUSD` directly to the Yearn vault contract address.
   - This doubled the `totalAssets()` while leaving `totalSupply()` unchanged.
   - Consequently, `getPricePerShare()` doubled in value instantly.
5. **Cream's Oracle Sees Hyper-Inflated Collateral**:
   - Cream's oracle queried the manipulated `getPricePerShare()` and calculated that the attacker's `cyUSD` collateral was worth over $1.5 Billion.
6. **Drain Borrowing**:
   - Using the fake $1.5B collateral value, the attacker borrowed all available liquid assets in Cream (ETH, WBTC, DAI, USDC, UNI).
7. **Repay Flash Loans**: Attacker repaid the MakerDAO and Aave flash loans and kept ~$130M in stolen assets.

---

## Official Remediation & Code Diff
1. **Time-Weighted Average Pricing (TWAP)**: Abandon spot share price reads and require multi-block TWAP or decentralized off-chain oracles (Chainlink feeds).
2. **Cap Borrowing Power on Illiquid Collateral**: Enforce strict borrow caps on synthetic and wrapped LP tokens.
3. **Internal Solvency Bounds**: Revert if oracle price diverges by more than 2% within a single block.

---

## Key Counterfactual Invariant
- **Invariant**: *Lending collateral valuations must never be derived from manipulable spot balances of single liquidity pools or donation-sensitive share rates within the same block.*
- **Counterfactual Hypothesis**: *If Cream had required a Chainlink decentralized price feed or a 30-minute TWAP oracle instead of spot `getPricePerShare()`, the donation would have had 0% impact on the collateral calculation within the attack transaction, preventing the $130M borrow drain.*
