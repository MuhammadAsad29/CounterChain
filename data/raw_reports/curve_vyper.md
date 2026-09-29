# Exploit Post-Mortem: Curve Finance / Vyper Reentrancy Malfunction ($73M)

## Incident Overview
- **Protocol**: Curve Finance (alETH, msETH, pETH pools)
- **Loss Amount**: ~$73.5 Million
- **Incident Date**: July 30, 2023
- **Network**: Ethereum Mainnet
- **Vulnerability Category**: Compiler Bug / Storage Slot Collision / Cross-Function Reentrancy
- **Official Sources**: DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20230730-Curve_alETH`), Vyper GitHub Advisory (`GHSA-5v3x-2vq6-p58x`), Rekt.news

---

## Background & Architecture
Curve Finance is the preeminent automated market maker (AMM) optimized for pegged assets (stables, liquid staking derivatives). Certain flagship pools (such as the `alETH/ETH`, `pETH/ETH`, and `CRV/ETH` factory pools) were written in Vyper and compiled with compiler versions `0.2.15`, `0.2.16`, and `0.3.0`.

To prevent reentrancy attacks during liquidity operations, the contracts used Vyper's built-in `@nonreentrant("lock")` decorator on pool interaction functions (`remove_liquidity`, `add_liquidity`, `exchange`).

---

## Vulnerable Smart Contract & Compiler Logic
In Vyper versions 0.2.15, 0.2.16, and 0.3.0, the compiler had a critical bug in how it allocated storage slots for the reentrancy lock keys:

```python
# Vyper pool contract snippet
@external
@nonreentrant('lock')
def remove_liquidity(_amount: uint256, min_amounts: uint256[N_COINS]) -> uint256[N_COINS]:
    # Burn LP tokens
    # Send ETH and tokens to user (External raw_call triggering ETH fallback)
    raw_call(msg.sender, b"", value=eth_amount)
    # Update internal pool state balances

@external
@nonreentrant('lock')
def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256) -> uint256:
    # Mint LP tokens based on current pool virtual price
    ...
```

### The Root Cause: Compiler Reentrancy Lock Collision
The compiler assigned a storage slot for the reentrancy key based on each function's AST context rather than a shared global contract slot. Consequently:
- `remove_liquidity` used storage slot `0` for its reentrancy lock.
- `add_liquidity` used storage slot `1` for its reentrancy lock.

Even though both functions explicitly declared `@nonreentrant('lock')` with the **same lock key name**, the compiled bytecode wrote to **different storage slots**. A caller inside the ETH transfer callback from `remove_liquidity` could freely reenter `add_liquidity` because slot `1` remained unlocked (`0`)!

---

## Step-by-Step Attack Vector
1. **Flash Loan Ingestion**: Attacker flash-borrowed WETH and raw ETH.
2. **Initial Liquidity Add**: Attacker deposited ETH into the Curve `alETH/ETH` pool, receiving LP tokens.
3. **Trigger Remove Liquidity**: Attacker invoked `remove_liquidity` to withdraw assets.
4. **Reentrancy Hijack**:
   - As Curve sent native ETH to the attacker contract via `raw_call`, the attacker's fallback function was executed.
   - At this precise instant, the pool's ETH balance had decreased, but the internal LP total supply accounting had not finalized.
   - The attacker called `add_liquidity` inside the fallback hook.
   - Because of the Vyper compiler bug, `add_liquidity` allowed the call to proceed.
5. **Virtual Price Distortion**:
   - The pool calculated LP token minting using an artificially deflated asset reserve balance, minting an excessive amount of new LP tokens to the attacker.
6. **Drain & Profit**: Attacker burned the inflated LP tokens, claiming both pool reserves and draining over $73M.

---

## Official Remediation
1. **Compiler Patch**: Vyper released patch in `0.3.1` and `0.3.8` ensuring all functions sharing a reentrancy lock key point to the identical global storage offset.
2. **Contract Remediation**: Curve migrated pools to Solidity or upgraded Vyper versions (`>= 0.3.7`) with verified nonreentrant global mutexes.

---

## Key Counterfactual Invariant
- **Invariant**: *When an account is in the middle of executing any state-mutating pool function, all other pool entrypoints sharing the mutex must revert immediately upon re-invocation.*
- **Counterfactual Hypothesis**: *If the contract had been compiled with Vyper 0.3.1+ (or protected by a shared global Solidity mutex wrapper), the reentrant call to `add_liquidity` during the ETH transfer callback would have reverted with 'reentrant call', completely stopping the $73M drain.*
