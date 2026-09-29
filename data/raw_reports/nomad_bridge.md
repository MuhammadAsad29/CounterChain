# Exploit Post-Mortem: Nomad Bridge Replica Initialization Exploit ($190M)

## Incident Overview
- **Protocol**: Nomad Token Bridge
- **Loss Amount**: ~$190.7 Million
- **Incident Date**: August 1, 2022
- **Network**: Ethereum Mainnet, Moonbeam
- **Vulnerability Category**: Access Control / Uninitialized Zero Root Validation
- **Official Sources**: Paradigm Security Post-Mortem (samczsun), Rekt.news (Nomad Bridge Exploit), DeFiHackLabs (`SunWeb3Sec/DeFiHackLabs#20220801-NomadBridge`)

---

## Background & Architecture
Nomad is an optimistic cross-chain messaging bridge. Off-chain updaters sign messages containing fraud-provable Merkle roots of transaction data.

In Nomad's `Replica.sol` contract, messages are validated against a Merkle root stored in a mapping:
```solidity
mapping(bytes32 => ConfirmAt) public acceptableRoot;
```
When a valid message batch is committed, its Merkle root is recorded with a confirmation timestamp. When a user requests to execute a bridged transaction, `Replica.process()` checks whether the message's root is acceptable.

---

## Vulnerable Smart Contract Logic
During an upgrade to `Replica.sol`, the Nomad team initialized the contract with a default configuration:

```solidity
// Vulnerable initialization in Replica.sol
function initialize(
    uint32 _remoteDomain,
    address _updater,
    bytes32 _committedRoot,
    uint256 _optimisticSeconds
) public initializer {
    ...
    // TEAM INITIALIZED _committedRoot AS 0x0000000000000000000000000000000000000000000000000000000000000000
    confirmAt[_committedRoot] = 1;
}

// In Replica.sol process() function:
function process(bytes memory _message) public returns (bool _success) {
    bytes32 _messageHash = keccak256(_message);
    require(acceptableRoot(messages[_messageHash]), "!acceptable root");
    ...
}

function acceptableRoot(bytes32 _root) public view returns (bool) {
    if (_root == bytes32(0)) {
        return false; // Intended guard
    }
    return confirmAt[_root] > 0 && block.timestamp >= confirmAt[_root];
}
```

### The Root Cause: Zero Hash Legitimation
Before a message is submitted and processed, an unproven message has `messages[_messageHash] == bytes32(0)`.
Because the team had marked `confirmAt[0x00] = 1`, and someone passed a call flow where `acceptableRoot` or the internal checks evaluated the empty root against `confirmAt`, the contract treated ANY arbitrary unproven message as automatically verified!

This allowed anyone to submit a transaction calling `Replica.process()` with a payload stating "Transfer 100 WBTC to my address", and the contract approved it without needing any valid bridge proof.

---

## Step-by-Step Attack Vector
1. **Initial Malicious Proof Discovery**: A hacker noticed that an upgrade transaction had legitimized the zero root `0x00...`.
2. **Forged Withdrawal Transaction**: Attacker submitted a fake bridge message payload directly to `process()` on Ethereum, directing 100 WBTC to their wallet.
3. **Automatic Approval**: `Replica.sol` checked `confirmAt[0x00] > 0`, which returned true (`1`).
4. **Immediate Bridge Drain**: The bridge disbursed 100 WBTC.
5. **The Decentralized Copycat Frenzy**:
   - Because the attack did not require special keys or complex flash loans, observers saw the transaction on Etherscan.
   - Dozens of bot operators and copycats copied the attacker's transaction data, replaced the recipient address with their own wallet, and re-broadcast the transaction.
   - Within hours, over $190M was drained by over 300 independent copycat addresses.

---

## Official Remediation
```diff
function acceptableRoot(bytes32 _root) public view returns (bool) {
-   if (_root == bytes32(0)) { return false; }
+   // Strictly disallow zero root regardless of confirmAt mapping state
+   require(_root != bytes32(0), "Nomad: zero root invalid");
    return confirmAt[_root] > 0 && block.timestamp >= confirmAt[_root];
}
```

---

## Key Counterfactual Invariant
- **Invariant**: *A cross-chain bridge must never accept unproven or null Merkle roots as valid execution authorizations.*
- **Counterfactual Hypothesis**: *If `confirmAt[bytes32(0)]` had never been initialized to 1, or if `process()` strictly asserted that `messages[_messageHash] != bytes32(0)`, all arbitrary process calls would have reverted with '!acceptable root', completely preventing the $190M drain.*
