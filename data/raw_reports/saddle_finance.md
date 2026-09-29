# Official Incident Analysis: Saddle Finance MetaSwap Exploit ($11M)

## Official Metadata & Provenance
- **Protocol**: Saddle Finance (MetaSwap Stable AMM)
- **Reported Loss**: ~$11 Million (in sUSD, USDC, DAI)
- **Incident Date**: April 30, 2022
- **Network**: Ethereum Mainnet
- **Vulnerability Category**: Mathematical Precision / Virtual Price Computation Flaw
- **Primary Official Sources**:
  - OpenZeppelin Official Incident Post-Mortem: `https://blog.openzeppelin.com/saddle-finance-exploit-post-mortem/`
  - BlockSec Official Exploit Root-Cause Analysis: `https://blocksecteam.medium.com/saddle-finance-exploit-root-cause-analysis-96942ad26b80`
  - Rekt.news Official Post-Mortem: `https://rekt.news/saddle-finance-rekt/`
  - DeFiHackLabs GitHub Reproduction: `SunWeb3Sec/DeFiHackLabs` (`SaddleFinance_exp.sol`)

---

## Technical Architecture & Background
Saddle Finance is an AMM designed for low-slippage trading between pegged crypto assets based on the Curve StableSwap invariant algorithm.

In Saddle's MetaSwap implementation, the protocol allowed pairing a single synthetic token (such as `sUSD`) against an entire existing Saddle base LP pool (such as `saddleUSD-V2`, consisting of DAI/USDC/USDT). To price trades across the meta-pool, the contract calculated the virtual price of the underlying LP token to maintain parity between assets of different decimals.

---

## Vulnerable Smart Contract Logic
In Saddle's `SwapUtils.sol` / `MetaSwapUtils.sol`:

```solidity
// Vulnerable calculation in calculateSwap
function calculateSwap(
    Swap storage self,
    uint8 tokenIndexFrom,
    uint8 tokenIndexTo,
    uint256 dx
) external view returns (uint256) {
    ...
    // VULNERABILITY: Rounding and precision discrepancy in base pool LP valuation
    // The contract failed to account for precision scaling when converting between
    // base pool virtual price and meta-pool tokens with differing decimal scales.
    uint256 baseVirtualPrice = baseSwap.getVirtualPrice();
    ...
}
```

### The Root Cause: Precision Scaling & Imbalanced Reserves
The implementation failed to correctly normalize the virtual price calculation during asymmetric trades when the pool had heavily skewed reserves. An attacker could use a flash loan to flood one side of the base pool, skew the virtual price calculation, and execute an inverted swap where the contract returned an excessive quantity of the opposite asset due to an arithmetic rounding error in `SwapUtils.sol`.

---

## Step-by-Step Attack Vector
1. **Flash Loan Ingestion**: Attacker flash-borrowed 10M sUSD, 15M USDC, and 20M DAI from Aave.
2. **Asymmetric Swap Injection**:
   - Attacker executed large unbalanced swaps in the Saddle `sUSD` MetaSwap pool.
   - This depressed the calculated invariant `D` within the internal numerical solver.
3. **Exploiting Precision Loss**:
   - The contract’s convergence check in `getYD()` exited prematurely due to precision loss when virtual prices diverged from unity (`1.0`).
   - The attacker received an inflated amount of `saddleUSD-V2` LP tokens relative to the input `sUSD`.
4. **Liquidity Extraction**:
   - Attacker redeemed the LP tokens for real DAI, USDC, and USDT from the underlying base pool.
5. **Drain & Profit**: Attacker extracted over $11M in net assets, repaid the flash loans, and routed profits through Tornado Cash (with ~$3.8M rescued by BlockSec whitehats).

---

## Official Remediation
```diff
- uint256 baseVirtualPrice = baseSwap.getVirtualPrice();
+ // REMEDIATION: Enforce strict precision normalization and verify convergence threshold
+ require(baseVirtualPrice >= MIN_VIRTUAL_PRICE && baseVirtualPrice <= MAX_VIRTUAL_PRICE, "Virtual price out of bounds");
+ // Fix convergence loop in getYD to iterate until difference is strictly < 1 wei
```

---

## Key Counterfactual Invariant
- **Invariant**: *MetaSwap virtual price convergence algorithms must strictly bound output precision and revert if calculated invariant deviation exceeds 0.1% of fair reserve ratio.*
- **Counterfactual Hypothesis**: *If Saddle had enforced bounds on baseVirtualPrice or fixed the numerical convergence precision in `getYD()`, the distorted swap transaction would have reverted with 'Virtual price out of bounds', completely preventing the $11M drain.*
