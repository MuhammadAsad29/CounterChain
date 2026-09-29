# Official Incident Analysis: Harvest Finance Flash Loan Arbitrage ($33.8M)

## Official Metadata & Provenance
- **Protocol**: Harvest Finance
- **Reported Loss**: ~$33.8 Million (in USDC and USDT)
- **Incident Date**: October 26, 2020
- **Network**: Ethereum Mainnet
- **Vulnerability Category**: Economic / Flash Loan Virtual Price Manipulation of Curve Y-Pool
- **Primary Official Sources**:
  - PeckShield Official Incident Analysis: `https://peckshield.medium.com/harvest-finance-incident-analysis-y-pool-manipulation-16275ddf7a9d`
  - Rekt.news Official Post-Mortem: `https://rekt.news/harvest-finance-rekt/`
  - DeFiHackLabs GitHub Reproduction: `SunWeb3Sec/DeFiHackLabs` (`Harvest_exp.sol`)
  - Harvest Finance Core Team Official Post-Mortem

---

## Technical Architecture & Background
Harvest Finance is a yield aggregation protocol. Users deposited stablecoins (USDT, USDC, DAI) into Harvest Vaults (`fUSDT`, `fUSDC`). Harvest deployed these stablecoins into underlying yield-generating protocols, primarily Curve's Y-pool (`yUSDC`, `yUSDT`, `yDAI`, `yTUSD`).

To calculate how many `fUSDT` shares to mint upon deposit (and how many underlying tokens to return upon withdrawal), Harvest calculated the share price based on the pool's asset value divided by total shares:
$$\text{PricePerShare} = \frac{\text{Total Assets}}{\text{Total Supply}}$$
Harvest calculated `Total Assets` by querying Curve Y-pool's `get_virtual_price()`.

---

## Vulnerable Smart Contract Logic
In Harvest Finance's `Vault.sol` / `Strategy.sol`:

```solidity
// Vulnerable share calculation in Harvest Vault
function getPricePerFullShare() public view returns (uint256) {
    // Total underlying balance queried dynamically from Curve Y-pool
    return underlyingBalanceWithInvestment().mul(1e18).div(totalSupply());
}
```

### The Root Cause: Intra-Block Virtual Price Sensitivity
Harvest evaluated share value based on the instantaneous spot state of the Curve Y-pool. If the proportions of stablecoins in the Curve pool are dramatically unbalanced within a single transaction, the Curve `virtual_price` calculation fluctuates.

Because Harvest accepted deposits and processed withdrawals within the same block without a deposit fee or time delay, an attacker could manipulate the Curve pool balance, deposit into Harvest at an artificially depressed share price, rebalance the Curve pool, and withdraw at an inflated share price — capturing risk-free arbitrage.

---

## Step-by-Step Attack Vector
1. **Flash Loan Ingestion**: Attacker flash-borrowed 50M USDC and 18M USDT from Uniswap v2.
2. **Swap to Skew Curve Pool**:
   - Attacker swapped 17.2M USDT for USDC in Curve's Y-pool.
   - This flooded the pool with USDT, inflating the relative price of USDC in Curve and driving down the Y-pool virtual price.
3. **Deposit into Harvest Vault at Discount**:
   - Attacker deposited 49.9M USDC into Harvest's `fUSDC` vault.
   - Because of the depressed virtual price, Harvest minted an excessive amount of `fUSDC` shares to the attacker.
4. **Swap Back to Rebalance Curve**:
   - Attacker swapped 19.4M USDC back for USDT in the Curve Y-pool.
   - This restored or boosted the Curve Y-pool virtual price.
5. **Withdraw from Harvest at Premium**:
   - Attacker withdrew their `fUSDC` shares.
   - Because the share price had recovered to fair value, the attacker received more USDC than they originally deposited.
6. **Repeat Cycle**: The attacker repeated this loop 17 times within minutes, draining $33.8M.
7. **Repay Flash Loans**: Attacker repaid the Uniswap v2 flash loan, walking away with $24.7M net profit.

---

## Official Remediation
1. **Commit-Reveal / Deposit Timelocks**: Enforce that funds deposited into a vault cannot be withdrawn within the same block.
2. **Slippage Bounds on Virtual Price**: Limit accepted virtual price fluctuations to <0.5% per transaction.
3. **Decentralized Oracles**: Use Chainlink or multi-block TWAP to value vault assets rather than manipulable spot AMM pool balances.

---

## Key Counterfactual Invariant
- **Invariant**: *A vault must not allow deposit and withdrawal of capital within the same block when share valuation depends on spot AMM reserve ratios.*
- **Counterfactual Hypothesis**: *If Harvest had enforced a 1-block delay between deposit and withdrawal (or capped intra-block share price divergence), the same-transaction arbitrage loop would have reverted, preventing the $33.8M drain.*
