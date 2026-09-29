# Exploit Post-Mortem: Mango Markets ($114M Exploit)

## Incident Overview
- **Protocol**: Mango Markets v3
- **Loss Amount**: ~$114 Million
- **Incident Date**: October 11, 2022
- **Network**: Solana
- **Vulnerability Category**: Oracle Price Manipulation / Illiquid Perpetual Futures Mark Price Manipulation
- **Official Sources**: DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20221011-MangoMarkets`), Rekt.news (Mango Markets Exploit), Mango DAO Post-Mortem

---

## Background & Architecture
Mango Markets was a decentralized trading platform on Solana offering cross-margin lending, borrowing, and perpetual futures contracts. Users deposited collateral (such as USDC, SOL, BTC) and could trade leveraged perpetuals.

Mango's risk engine determined an account's unrealized profit & loss (uPnL) and allowed accounts with high unrealized profits to borrow other protocol assets against their position value. The mark price for MNGO perpetual contracts was derived from an oracle that factored in the order book mid-price on low-liquidity markets.

---

## Vulnerable Protocol Logic
Mango allowed positions in the `MNGO-PERP` contract to be valued dynamically against an order book with very thin depth:

```rust
// Mango perpetual mark price evaluation logic
fn get_mark_price(order_book: &OrderBook, oracle_price: Price) -> Price {
    let best_bid = order_book.get_best_bid();
    let best_ask = order_book.get_best_ask();
    
    // In low liquidity, mid-price can be moved with small capital
    let mid_price = (best_bid + best_ask) / 2;
    mid_price
}
```

### The Root Cause: Thin Liquidity & Self-Trading
The attacker funded two separate accounts (Account A and Account B) with 5M USDC each. Because the market for `MNGO-PERP` was illiquid and had no position size caps relative to open interest, the attacker could self-trade between Account A and Account B, aggressively buying on the order book to drive the MNGO spot and perp mark price from $0.03 to $0.91 within 20 minutes (a 3,000% increase).

---

## Step-by-Step Attack Vector
1. **Fund Two Separate Accounts**:
   - Account A deposited 5M USDC.
   - Account B deposited 5M USDC.
2. **Open Massive Opposite Positions**:
   - Account A shorted 483M MNGO perps at $0.038.
   - Account B went long 483M MNGO perps at $0.038.
   - Net exposure across both accounts was zero.
3. **Order Book Pumping**:
   - Attacker used a third pool of capital to purchase MNGO on spot markets (AscendEX, Raydium, Mango spot), pushing the spot oracle price to $0.91.
4. **Unrealized PnL Ballooning**:
   - With MNGO priced at $0.91, Account B's long position showed an unrealized paper profit of over $400 Million.
5. **Borrow All Liquid Assets**:
   - Mango's margin engine allowed Account B to borrow against this paper uPnL.
   - Account B borrowed $114M in liquid assets (USDC, MSOL, BTC, ETH, USDT), completely emptying Mango's lending liquidity pools.
6. **Abandon Account A**: Account A was liquidated into massive bad debt, while Account B extracted all real cash.

---

## Official Remediation
1. **Cap Borrowing Against Unrealized PnL**: Unrealized paper gains in perpetuals must never be directly borrowable as liquid collateral.
2. **Position Size Limits Relative to Open Interest**: Hard caps on position sizes prevent a single actor from dominating market liquidity.
3. **Medianized Multi-Source Oracles**: Enforce robust oracles with circuit breakers if price deviates more than 5% from broader market depth.

---

## Key Counterfactual Invariant
- **Invariant**: *Unrealized paper profits on volatile or illiquid perpetual contracts must not serve as cash collateral for borrowing external lending pool reserves.*
- **Counterfactual Hypothesis**: *If Mango had disallowed borrowing against unrealized perpetual PnL, or capped collateral value to initial deposits + realized gains, Account B would have been unable to borrow liquidity, preventing the $114M protocol insolvency.*
