# AgentResolve v2.3.0 — Architecture

AgentResolve is organized around one evidence chain:

```text
USER REQUEST
    ↓
SHOPPING AGENT
    ↓
EXECUTION TRACE
    ↓
AUTHORIZATION
    ↓
CHECKOUT / PAYMENT
    ↓
FULFILLMENT / DELIVERY / REFUND
    ↓
DISPUTE
    ↓
EVIDENCE RECONSTRUCTION
    ↓
INCIDENT IDENTIFICATION
    ↓
CANONICAL FORENSIC RULES
    ↓
ATTRIBUTION
    ↓
PREVENTABILITY
    ↓
COUNTERFACTUAL
    ↓
REPORT
```

## Layers

### Agent layer

Produces transaction execution evidence. Low-level validation events are the preferred source for determining whether a validation occurred.

### Merchant/payment layer

Controlled deterministic simulation. It creates believable lifecycle state transitions without moving real funds.

### Domain model

Pydantic contracts preserve legacy transaction fields and add optional lifecycle, authorization, payment, fulfillment, generalized attribute, trace and provenance data.

### Incident engine

Answers **what happened** operationally.

### Canonical forensic engine

Answers **what fault attribution is supported** under the six-category evidence rules.

### Scoring / preventability / counterfactual

Transforms rule evidence into normalized attribution, preventability and deterministic replay results.

### Explanation layer

May summarize deterministic findings, but cannot alter incident, attribution, scores, evidence, preventability or missing-data status.

### Dashboard

A compact forensic workstation presenting the evidence chain visually.

## Evidence integrity

New simulated events may be hash-linked:

```text
hash(E0)
  ↓ parent
hash(E1)
  ↓ parent
hash(E2)
```

These hashes verify internal consistency of the recorded simulation. They are not independent third-party notarization.
