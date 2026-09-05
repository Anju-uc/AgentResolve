# AgentResolve — Implementation Plan

**Version:** 2.3.0

## 0. Objective

Build AgentResolve as a compact but believable transaction-forensics platform for AI-agent commerce.

The target flow is:

```text
Natural-language purchase request
 -> shopping-agent execution
 -> authorization
 -> checkout
 -> payment
 -> fulfillment
 -> delivery / refund
 -> dispute
 -> evidence reconstruction
 -> incident identification
 -> deterministic attribution
 -> preventability
 -> counterfactual
 -> explanation-only LLM
 -> forensic report / evidence packet
```

The system remains a controlled simulation for development and demonstration. The simulation records evidence using the same lifecycle concepts that a real transaction operations system would need.

## 1. Engineering Principles

1. Preserve the original six canonical fault categories.
2. Preserve existing benchmark behavior as a regression contract.
3. Separate incident type from fault attribution.
4. Derive agent behavior from execution evidence rather than trusting self-reported summaries when lower-level trace exists.
5. Generalize commerce attributes without breaking the existing standard fields.
6. Record evidence provenance and integrity metadata.
7. Separate economic harm from attribution.
8. Keep the LLM explanation-only.
9. Keep the codebase modular and small.
10. Keep simulation clearly labeled.
11. Do not hide uncertainty, missing evidence, or contradictory evidence.
12. Do not introduce infrastructure merely for appearance.

## 2. Architecture

```text
agent/                  shopping-agent execution + trace
merchant/               controlled merchant and payment simulation
        |
        v
app/models/              transaction + lifecycle + evidence contracts
        |
        v
app/engine/incidents.py  incident identification
app/engine/rules.py      canonical five-rule attribution checks
app/engine/helpers.py    comparison + evidence helpers
app/engine/scoring.py    canonical attribution normalization
app/engine/preventability.py
app/engine/counterfactual.py
app/engine/provenance.py
app/engine/drift.py
        |
        v
app/engine/analyzer.py  unified deterministic case analysis
        |
        +--> app/llm/explainer.py
        +--> app/reports/report_builder.py
        +--> app/reports/pdf_packet.py
        |
        v
api/routes.py            backend endpoints
        |
        v
dashboard/app.py       forensic workstation UI
```

No microservices, queues or production database are required for this version.

## 3. Phase 1 — Baseline Protection

Before implementation changes:

- inspect the current repository;
- read `rules.md`;
- run the complete regression suite;
- record the baseline count/result;
- identify backward-compatibility risks.

Do not refactor unrelated code during baseline protection.

Acceptance:

```bash
pytest
```

passes before the new feature work begins.

## 4. Phase 2 — Domain Contract

Extend transaction models without invalidating existing JSON.

Required areas:

```text
UserRequest
Constraints
AgentInterpretation
MerchantSnapshot
AgentDecision
Dispute
Transaction
TransactionLifecycle
IncidentResult
EvidenceItem
RuleResult
AnalysisResult
```

Add optional support for:

- authorization records
- payment records
- fulfillment records
- refund records
- inventory records
- commercial adjustment records
- integration records
- agent execution traces
- generalized attributes
- evidence provenance
- direct economic harm
- dispute-drift supporting signals

Preserve `None` as unspecified.

## 5. Phase 3 — Execution Trace

Create a deterministic trace contract for the simulated shopping agent.

Each event should contain:

```text
event_id
timestamp
action
tool
arguments
result
status
content_hash
parent_hash
```

Validation events are derived from the trace.

Legacy `validation_steps_performed` remains for compatibility but is not authoritative when trace data exists.

## 6. Phase 4 — Generalized Attributes

Standard fields such as price, RAM, storage, seller and delivery remain available.

Add a generic attribute layer capable of representing:

```text
constraint
operator
advertised
checkout
delivered
metadata
```

The comparison layer must support the documented operators.

Add tests for numeric, string, list and arbitrary custom attributes.

## 7. Phase 5 — Evidence Provenance

Implement a lightweight integrity chain for newly generated lifecycle events.

Record:

```text
event_id
content_hash
parent_hash
capture_method
integrity_status
```

Implement verification:

```text
VERIFIED
UNVERIFIED
INVALID
```

Legacy records without hashes must remain valid and visibly unverified.

The project must never represent its own simulated hashes as third-party notarization.

## 8. Phase 6 — Operational Incident Engine

Expand incident identification to support:

```text
UNAUTHORIZED_TRANSACTION
INCORRECT_AMOUNT
WRONG_MERCHANT_OR_PAYEE
WRONG_ITEM_OR_VARIANT
NON_DELIVERY
PRODUCT_DEFECT
FULFILLMENT_ERROR
RETURN_REFUND_FAILURE
PAYMENT_PROCESSING_FAILURE
AUTHORIZATION_SCOPE_AMBIGUITY
AUTHORIZATION_SCOPE_VIOLATION
INVENTORY_RACE
FEE_TAX_SURPRISE
PROMOTION_FAILURE
DUPLICATE_CHARGE
SYSTEM_INTEGRATION_FAILURE
```

Incident identification must inspect the lifecycle and recorded evidence.

It must not simply map a scenario name directly to a finding.

## 9. Phase 7 — Canonical Fault Engine Preservation

Keep the five independent canonical rule checks:

```text
USER_AMBIGUITY
AGENT_MISJUDGMENT
MERCHANT_DATA_ERROR
EXTERNAL_CHANGE
USER_POST_PURCHASE_CHANGE
```

Do not rewrite their semantics merely to improve demonstration cases.

Agent misjudgment should use execution-derived validation status when available.

All five canonical rules must execute independently.

## 10. Phase 8 — Economic Harm

Add separate measurement for direct financial impact when the record establishes it.

Examples:

```text
captured - authorized
checkout - listing
expected refund - received refund
duplicate capture amount
```

Do not manufacture values from incomplete evidence.

## 11. Phase 9 — Dispute Drift Support

Implement a deterministic supporting comparison between:

```text
original request
later dispute
```

Expose:

```text
similarity
new terms
likely preference drift
methodology
```

This signal is supportive and never authoritative over explicit transaction evidence.

## 12. Phase 10 — Forensic Analyzer

The unified analyzer must produce:

```text
incident
status
canonical attribution
contributors
operational responsibility where recorded
economic harm
evidence status
missing evidence
evidence items
rule ledger
preventability
counterfactual
dispute drift
data flags
explanation state
```

The deterministic result must be complete before explanation generation.

## 13. Phase 11 — Shopping Agent

Provide a natural-language purchase entry point.

The agent must:

1. parse the request;
2. search products;
3. compare candidates;
4. check constraints;
5. record authorization;
6. validate checkout;
7. capture payment in simulation;
8. create order;
9. record fulfillment state;
10. expose the resulting transaction for investigation.

When validation is enabled and no compliant product exists, the agent must not silently purchase an invalid candidate.

An explicit user override must be recorded as an event.

## 14. Phase 12 — Controlled Merchant and Payment Simulation

Provide deterministic simulation for:

- merchant listing changes
- checkout price changes
- seller substitution
- wrong variant
- delivery delay
- non-delivery
- product defect
- fulfillment quantity mismatch
- refund failure
- payment failure / pending / unknown
- duplicate charge
- inventory race
- tax/fee surprise
- promotion failure
- agent-to-merchant payload mismatch

Each scenario must produce evidence through lifecycle events rather than directly inserting an answer into the analyzer.

## 15. Phase 13 — Investigation Workstation

Build a restrained forensic dashboard.

### Overview

Display:

```text
Investigations
High-risk findings
Insufficient evidence
Incident classes
Recent investigations
Incident distribution
Attribution distribution
```

Avoid dashboard overload.

### Investigation

The main case view should prioritize:

```text
incident header
forensic verdict
visual diff matrix
validation black box
timeline audit
rule ledger
attribution
economic harm
preventability
counterfactual
provenance
explanation
raw forensic report
```

### Visual design

The UI should feel like a forensic/risk operations workstation:

- deep charcoal background
- subtle navy surfaces
- thin borders
- compact evidence labels
- cyan/teal investigative accent
- amber warnings
- restrained red divergence markers
- monospace IDs/hashes
- minimal decoration
- strong typography
- clear information hierarchy

The dashboard must present the product idea quickly rather than bury it under charts.

## 16. Phase 14 — Evidence Visualization

The visual diff must compare:

```text
User Stated
Merchant Advertised
Checkout
Delivered
```

The validation view must show the constraint and the low-level validation event.

The timeline must show chronological transaction events.

The provenance view must show hashes/integrity status when present.

## 17. Phase 15 — Forensic Evidence Packet

Provide exportable report data and a printable PDF packet.

Packet contents should include:

```text
transaction metadata
incident
canonical attribution
contributors
economic harm
preventability
evidence trace
provenance information when present
counterfactual
explanation disclaimer
```

State explicitly that the packet is an evidence presentation generated from recorded/simulated evidence and is not a legal liability decision.

## 18. Phase 16 — API

Preserve:

```text
GET  /health
GET  /cases
GET  /cases/{transaction_id}
POST /analyze
```

Add where useful:

```text
POST /agent/execute
GET  /transactions/{transaction_id}
POST /disputes
GET  /investigations
GET  /investigations/{transaction_id}
```

Routes delegate to domain services and must not reproduce forensic rules.

## 19. Phase 17 — Evaluation

Keep the original:

```text
20 development cases
10 holdout cases
```

Treat them as a synthetic deterministic regression/invariant corpus.

Do not claim that 100% accuracy represents production accuracy.

Run the evaluator twice and compare outputs.

Add separate tests for operational incidents and forensic infrastructure.

## 20. Phase 18 — Testing

Regression tests must cover:

### Existing behavior

- all original six categories
- multi-fault
- insufficient evidence
- duplicate-charge flag
- boundary comparisons
- preventability
- counterfactual
- LLM unavailable
- API behavior

### New functionality

- execution-derived validation
- validation trace contradiction
- generic attributes
- generic comparison operators
- provenance hash chain
- invalid chain detection
- authorization ambiguity
- authorization violation
- unauthorized transaction
- incorrect amount
- wrong merchant
- wrong variant
- non-delivery
- product defect
- fulfillment error
- refund failure
- payment pending/unknown
- duplicate charge
- inventory race
- fee/tax surprise
- promotion failure
- system integration mismatch
- dispute drift support signal
- economic harm
- printable report generation

## 21. Phase 19 — Final QA

Run:

```bash
pytest
python -m evaluation.evaluate
```

Run the benchmark twice.

Verify:

```text
same input
 -> same deterministic analysis
 -> same incident
 -> same attribution
 -> same scores
 -> same preventability
 -> same counterfactual
```

Manually inspect the dashboard for visual clarity and forensic hierarchy.

## 22. Documentation

Keep these synchronized:

```text
rules.md
IMPLEMENTATION_PLAN.md
README.md
docs/architecture.md
```

Documentation must clearly distinguish:

```text
canonical fault attribution
operational incident classification
economic harm
preventability
simulation boundaries
synthetic regression results
```

Do not include implementation prompts in this plan.

## 23. Definition of Done

### Engine

- [ ] six canonical fault categories preserved
- [ ] five canonical rules independently executed
- [ ] operational incident layer implemented
- [ ] generalized attributes supported
- [ ] execution trace supported
- [ ] provenance supported
- [ ] economic harm separated
- [ ] dispute drift support signal implemented
- [ ] missing evidence handled explicitly
- [ ] deterministic outputs preserved

### Product

- [ ] shopping-agent natural-language flow
- [ ] authorization evidence
- [ ] payment lifecycle
- [ ] fulfillment lifecycle
- [ ] dispute lifecycle
- [ ] Test Lab separated from normal user flow
- [ ] investigation workstation
- [ ] visual diff
- [ ] validation black box
- [ ] timeline audit
- [ ] provenance view
- [ ] printable evidence packet

### Evaluation

- [ ] 30-case regression corpus preserved
- [ ] development/holdout split preserved
- [ ] deterministic repeated evaluation
- [ ] operational incident tests separate
- [ ] no production-accuracy overclaim

### QA

- [ ] pytest passes
- [ ] compile checks pass
- [ ] API tests pass
- [ ] dashboard imports successfully
- [ ] report export works
- [ ] no unnecessary infrastructure added
