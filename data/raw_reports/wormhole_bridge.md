# Official Incident Analysis: Wormhole Token Bridge Exploit ($326M)

## Official Metadata & Provenance
- **Protocol**: Wormhole Cross-Chain Bridge (Solana Core Bridge)
- **Reported Loss**: 120,000 Wrapped ETH (~$326,000,000 USD)
- **Incident Date**: February 2, 2022
- **Chains Affected**: Solana, Ethereum
- **Vulnerability Category**: Signature Verification Bypass / Deprecated Instruction Substitution
- **Primary Official Sources**:
  - CertiK Security Incident Analysis: `https://www.certik.com/resources/blog/wormhole-bridge-exploit-incident-analysis`
  - Rekt.news Official Post-Mortem: `https://rekt.news/wormhole-rekt/`
  - DeFiHackLabs GitHub Reproduction: `SunWeb3Sec/DeFiHackLabs` (`Wormhole_exp.sol`)
  - Jump Crypto Public Incident Report

---

## Technical Architecture & Background
The Wormhole Token Bridge connects Solana to Ethereum and other EVM networks using a multi-signature federation called "Guardians". When assets are deposited on Solana, 19 designated Guardian nodes validate the transaction and sign a Validator Action Approval (VAA) message. A minimum threshold of 2/3 Guardians (13 out of 19) must sign the VAA before wrapped tokens (whETH) can be minted on Ethereum or Solana.

On Solana, Wormhole validated Guardian signatures through a specialized system program instruction (`verify_signatures`).

---

## Vulnerable Smart Contract Logic
In Solana's Wormhole implementation contract, the bridge verified Guardian signatures using the `verify_signatures` function in `verify_signature.rs`:

```rust
// Vulnerable verification logic in verify_signature.rs
pub fn verify_signatures(
    ctx: Context<VerifySignatures>,
    ...
) -> ProgramResult {
    let instruction_sysvar = &ctx.accounts.instruction_sysvar;
    
    // VULNERABILITY: load_current_index_checked was deprecated and bypassed
    // The contract accepted an untrusted user-supplied instruction sysvar account
    // instead of verifying that instruction_sysvar == solana_program::sysvar::instructions::id()
    let current_instruction = load_current_index_checked(&instruction_sysvar)?;
    ...
}
```

### The Root Cause: Unchecked Sysvar Account Substitution
Solana programs utilize the `Instructions` sysvar to inspect other instructions executed within the same transaction. The Wormhole contract intended to confirm that the native Solana `Secp256k1Program` had executed and verified the Guardians' signatures.

However, the contract failed to assert that the `instruction_sysvar` account passed into the transaction was indeed the genuine system instruction account (`sysvar::instructions::id()`). The attacker constructed a fake account populated with synthesized signature verification data and substituted it into the transaction. Wormhole accepted the fabricated verification data without checking the account address.

---

## Step-by-Step Attack Vector
1. **Account Fabrication**: Attacker generated a malicious account containing forged Guardian signatures matching the parameters for a 120,000 ETH mint.
2. **Instruction Sysvar Hijack**: Attacker invoked `verify_signatures`, passing the fabricated account address as the `instruction_sysvar`.
3. **Forged VAA Generation**: Because the account address was not checked, the contract marked the forged VAA as legitimate.
4. **Trigger `complete_wrapped` Mint**: Attacker invoked `complete_wrapped` on Solana, presenting the approved VAA.
5. **Mint 120,000 whETH**: Wormhole minted 120,000 wrapped ETH on Solana with zero collateral deposited.
6. **Bridge Drain to Ethereum**: Attacker bridged 93,750 ETH back to Ethereum via the legitimate bridge mechanism, extracting real ETH and leaving the bridge undercollateralized by $326M.

---

## Official Remediation
```diff
- let instruction_sysvar = &ctx.accounts.instruction_sysvar;
+ // REMEDIATION: Strictly verify that instruction_sysvar is the genuine Solana sysvar
+ require_keys_eq!(
+     *ctx.accounts.instruction_sysvar.key,
+     solana_program::sysvar::instructions::id(),
+     ErrorCode::InvalidSysvar
+ );
```

---

## Key Counterfactual Invariant
- **Invariant**: *Cross-chain signature verification must strictly enforce identity checks on system sysvars and reject any user-supplied fake verification accounts.*
- **Counterfactual Hypothesis**: *If Wormhole had asserted that `instruction_sysvar.key == sysvar::instructions::id()`, the fake signature account would have been rejected with `InvalidSysvar`, completely preventing the $326M mint.*
