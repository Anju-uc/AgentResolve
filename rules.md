# AgentResolve — Rules & Forensic Engine Specification

**Status:** Implementation contract  
**Version:** 2.3.0

## 1. Purpose

AgentResolve is an evidence-first transaction-forensics system for disputes arising from AI-agent commerce.

It answers:

> What does the recorded transaction evidence establish about what happened, what incident occurred, and what attribution is supported?

It does not determine hidden intent, moral or legal liability, or facts that were not recorded.

**Core principle: Evidence, not intent. Attribution, not legal blame.**

The system must prefer a documented inability to determine a cause over a guessed cause.

## 2. Product Model

AgentResolve has four separate concepts:

1. **Incident Type** — what happened operationally.
2. **Fault Attribution** — what the evidence supports about the cause.
3. **Economic Harm** — measurable direct financial impact when recorded.
4. **Preventability** — whether the issue was knowable before the relevant action.

They must never be collapsed into one label.

Example:

```text
INCIDENT:          INCORRECT_AMOUNT
PRIMARY ATTRIBUTION: AGENT_MISJUDGMENT
CONTRIBUTOR:       MERCHANT_DATA_ERROR
DIRECT HARM:       ₹30,000
PREVENTABILITY:    HIGH
```

An attribution score is a normalized evidence score, not probability, confidence, certainty, or legal liability.

## 3. Scope

### In scope

- structured and lifecycle transaction records
- natural-language shopping-agent simulation
- transaction authorization evidence
- payment and fulfillment evidence
- incident identification
- six canonical fault categories
- extended operational incident types
- generalized commerce attributes
- execution-trace-derived agent behavior
- evidence provenance and integrity metadata
- deterministic dispute-drift support signal
- multi-factor analysis
- evidence-based attribution scoring
- economic-harm measurement when recorded
- preventability
- counterfactual replay
- explanation-only LLM
- forensic report and printable evidence packet
- FastAPI
- Streamlit forensic workstation
- deterministic regression/evaluation suite

### Controlled-simulation boundary

Payment, merchant, fulfillment, integration, authorization and dispute events may be simulated deterministically for development and demonstration.

Simulation must be clearly labeled as simulation. Simulated hashes and evidence provenance must never be represented as independent external notarization.

### Out of scope

- moving real customer money
- real chargeback submission
- legal liability adjudication
- claiming official payment-network compliance
- external evidence notarization
- unrestricted production fraud detection
- hidden model reasoning as evidence
- unnecessary distributed infrastructure

## 4. Canonical Fault Categories

The original six categories remain stable and backward compatible:

### USER_AMBIGUITY

The disputed requirement was not recorded as an explicit constraint in the original request.

### AGENT_MISJUDGMENT

A requirement existed, the agent had access to it, the purchased state violated it, and the agent did not validate it before purchase.

All required conditions must hold:

```text
constraint exists
AND agent had constraint
AND purchased/selected state violates constraint
AND validation was not performed
```

### MERCHANT_DATA_ERROR

Merchant-provided information relied upon by the agent is inconsistent with checkout or another relevant merchant state.

### EXTERNAL_CHANGE

A condition satisfied its requirement at purchase and later changed so that the requirement was no longer satisfied.

### USER_POST_PURCHASE_CHANGE

A preference appears only after purchase and was absent from the original request.

This is a timeline finding, not a judgment about the user.

### NO_FAULT_DETECTED

Evidence is sufficient and none of the canonical fault checks fires.

## 5. INSUFFICIENT_EVIDENCE

`INSUFFICIENT_EVIDENCE` is a report state, not a fault category.

Return it when the evidence required for a determination is missing, null, malformed, contradictory in a way that blocks the determination, or unavailable.

Never infer a fault from missing evidence.

Example:

```json
{
  "status": "INSUFFICIENT_EVIDENCE",
  "missing_fields": ["merchant_snapshot.price_at_checkout"]
}
```

## 6. Operational Incident Taxonomy

Incident identification is separate from the six canonical fault rules.

Supported operational incident types include:

```text
NORMAL_PURCHASE
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

Operational incidents may have a recorded responsibility actor, but that actor is not a legal liability determination.

## 7. Deterministic Processing Order

```text
1. Validate schema
2. Check evidence completeness
3. Identify incident
4. Identify disputed field / attribute
5. Verify evidence integrity when provenance is supplied
6. Derive agent behavior from execution evidence
7. Run all five canonical fault checks independently
8. Run applicable operational attribution checks
9. Calculate economic harm when possible
10. Calculate attribution scores
11. Rank primary and contributing canonical faults
12. Determine preventability
13. Generate counterfactual replay
14. Generate supporting dispute-drift signal when possible
15. Optionally generate LLM explanation
16. Build final report / evidence packet
```

Never use first-match `if/elif` as the canonical fault classifier.

All five canonical fault checks must run independently.

## 8. Agent Execution Evidence

The legacy `validation_steps_performed` field is retained only for backward compatibility.

When low-level execution trace exists, it is authoritative for whether validation happened.

Validation should be derived from recorded execution events such as:

```text
validate_constraint
constraint_check
checkout_validation
```

A validation event should identify at minimum:

```text
field
expected value
observed/passed result
event_id
timestamp
```

Do not mark a validation as completed merely because the agent summary claims it was completed.

If a low-level execution trace contradicts a legacy checklist, use the execution trace for forensic analysis.

## 9. Authorization

Authorization evidence may contain:

```text
authorized amount
currency
authorization limit
authorized merchants
authorized categories
authorized constraints
user authorization status
final cart approval
consent timestamp
```

### Authorization scope ambiguity

Use when the recorded instruction is broad and the final cart lacks sufficient approval evidence to establish clear consent.

### Authorization scope violation

Use when an explicit authorized scope exists and recorded execution exceeds that scope.

Do not equate authorization scope violation with malicious behavior.

## 10. Generalized Attribute Model

The forensic model must not be limited to RAM, storage, price, seller, delivery and color.

For arbitrary attribute `X`, evidence may be represented as:

```text
X.constraint
X.operator
X.advertised
X.checkout
X.delivered
```

Examples include:

```text
cpu.cores
cpu.model
gpu.cores
screen.size
condition.grade
bundle.items
quantity
delivery.service_level
promotion.discount
tax.amount
fee.amount
```

Supported comparison semantics include:

```text
under       <
at_most     <=
minimum     >=
exactly     ==
gte         >=
lte         <=
eq          ==
contains
subset_of
```

Existing operator behavior must remain unchanged.

`under` is strictly less than.

## 11. Evidence Provenance

Every new evidence object should support provenance metadata:

```text
evidence_id
event_id
source_type
source_reference
capture_method
timestamp
content_hash
parent_hash
integrity_status
```

For lifecycle chains with hashes:

```text
E0 -> hash0
E1 -> hash1(parent=hash0)
E2 -> hash2(parent=hash1)
```

The verifier may report:

```text
VERIFIED
UNVERIFIED
INVALID
```

Legacy benchmark records without hashes remain valid and are explicitly `UNVERIFIED` rather than being treated as corrupted.

## 12. Dispute Drift

AgentResolve may compare the original request with the later dispute text using a deterministic supporting similarity/difference signal.

This signal may surface:

```text
new terms
similarity
likely preference drift
```

It must never independently determine fault, override explicit transaction evidence, or prove dishonesty.

## 13. Economic Harm

Economic harm is distinct from attribution.

When sufficient recorded amounts exist, expose direct measurable impact such as:

```text
captured amount - authorized amount
checkout amount - listed amount
missing refund amount
duplicate captured amount
```

Do not manufacture financial harm when the transaction record does not establish it.

## 14. Payment and Fulfillment Incidents

### PAYMENT_PROCESSING_FAILURE

Use recorded payment state such as `FAILED`, `PENDING`, `UNKNOWN`, `TIMEOUT`, or `UNCERTAIN` when the state prevents treating payment as a completed capture.

### DUPLICATE_CHARGE

A transaction/payment data flag and operational incident.

It is not one of the six canonical fault categories.

### NON_DELIVERY

Use when payment is recorded as captured and the fulfillment evidence establishes that the order was not shipped/delivered according to the recorded lifecycle.

### PRODUCT_DEFECT

Use when the expected item was delivered but reliable recorded evidence identifies a defect.

### FULFILLMENT_ERROR

Use when the fulfilled item, quantity or recorded fulfillment state differs from the ordered state.
For quantity mismatches, require both `expected_quantity` and `actual_quantity`; for variant mismatches, require both `expected_variant` and `actual_variant`.

### RETURN_REFUND_FAILURE

Use when a return is recorded as accepted or otherwise refund-eligible and the expected refund is not completed as recorded.

## 15. Commercial Changes

### FEE_TAX_SURPRISE

Use when checkout adds material taxes/fees that were not disclosed before authorization, provided the relevant evidence is recorded.

### PROMOTION_FAILURE

Use when a recorded promotion/discount was expected at the relevant pre-checkout stage and a later merchant state fails to apply it.

Do not assume every price difference is a fault; preserve the underlying breakdown.

## 16. System Integration

Use `SYSTEM_INTEGRATION_FAILURE` when the agent-side transaction intent or payload and the merchant-side recorded transaction materially disagree and both sides are available.

Examples:

```text
agent item = ITEM_A
merchant item = ITEM_B
```

or:

```text
agent quantity = 2
merchant quantity = 1
```

## 17. Inventory Race

Use when:

```text
available at selection = true
AND
available at checkout = false
AND
selection_timestamp is recorded
AND
checkout_timestamp is recorded
AND
checkout_timestamp > selection_timestamp
```

Stage-specific inventory flags without a complete, ordered timestamp pair do not establish an inventory race and must not be upgraded into one by inference.

## 18. Rule Evidence

Every fired canonical rule must provide:

```text
category
fired
evidence
evidence_factors
raw points
```

Every evidence statement must describe a recorded fact.

Rules identify evidence. Scoring converts evidence factors into attribution values.

## 19. Attribution Scoring

Canonical scores remain deterministic evidence-normalization values.

They are not probabilities or legal percentages.

Existing factor weights remain compatible unless explicitly revised by a documented contract change.

A separate economic-harm value must never be silently turned into a fault percentage.

## 20. Preventability

### HIGH

The problem was knowable before the relevant action and a recorded validation/action could have caught it.

### LOW

The problem became knowable only after the relevant action.

### N/A

Use when preventability cannot meaningfully be assigned under the case semantics, including no-fault/post-purchase preference cases where appropriate.

Preventability is independent of fault attribution and economic harm.

## 21. Counterfactual Replay

Counterfactual replay asks whether a defined preventative action would have changed the recorded action path.

Example:

```text
required storage = 256GB
observed storage = 128GB
hypothetical validation = performed
result = PURCHASE_WOULD_HAVE_BEEN_BLOCKED
```

Do not claim that the hypothetical proves an unrecorded real-world event.

## 22. LLM Boundary

The LLM is explanation-only.

It may summarize deterministic findings.

It must never determine or change:

```text
incident
fault category
score
preventability
economic harm
evidence validity
missing fields
```

If unavailable, deterministic analysis continues.

## 23. Dashboard Contract

The dashboard is a forensic workstation, not a form-entry CRUD screen.

### Overview

Show only the high-value operational information:

```text
Investigations
High-risk findings
Insufficient evidence
Incident classes
Recent investigations
Incident distribution
Attribution distribution
```

The dashboard must communicate the product within a few seconds and must not be chart-heavy.

### Investigation view

The primary investigation screen must contain:

```text
Incident Header
Forensic Verdict
Visual Diff Matrix
Validation Black Box
Timeline Audit
Evidence Provenance
Rule Ledger
Attribution
Economic Harm
Preventability
Counterfactual
Explanation
Raw Report
```

### Visual Diff Matrix

Compare:

```text
User Stated
Merchant Advertised
Checkout
Delivered
```

Meaningful divergences should be visually highlighted.

### Validation Black Box

Show:

```text
constraint
agent had constraint
validation event
observed value
validation result
```

### Forensic visual language

Use a restrained dark forensic workstation aesthetic:

- charcoal / deep navy surfaces
- thin muted borders
- compact uppercase evidence labels
- restrained cyan/teal investigative accent
- amber for warnings
- red only for material divergence
- green only for validated/cleared states
- monospace for IDs, hashes and raw evidence
- strong spacing and typography
- no excessive gradients or decorative animation

## 24. Test Lab

Controlled scenarios belong in a clearly labeled Test Lab.

Normal customer flow must not ask users to select a fault.

Scenarios should produce lifecycle evidence which AgentResolve then investigates.

## 25. Benchmark and Evaluation

The existing 30-case synthetic benchmark remains important and must not be discarded.

It is a deterministic regression/invariant suite.

It is not empirical proof of real-world accuracy.

Report:

```text
accuracy
macro precision
macro recall
macro F1
per-category metrics
confusion matrix
```

Run evaluation twice and verify identical results.

Do not tune holdout cases.

New operational incident tests remain distinguishable from the canonical benchmark.

## 26. Non-Negotiable Safety / Integrity Rules

```text
No guessing from missing evidence.
No hidden-intent claims.
No legal-liability claims.
No LLM fault classification.
No first-match canonical fault classification.
No silent non-compliant agent purchase.
No false evidence provenance.
No simulated evidence represented as external notarization.
No probability/confidence wording for heuristic attribution scores.
No holdout tuning.
No frontend duplication of forensic rules.
```

## 27. Definition of a Defensible Finding

A finding is defensible when a reviewer can follow:

```text
raw transaction
 -> lifecycle event
 -> evidence object
 -> provenance
 -> rule condition
 -> evidence factor
 -> attribution
 -> preventability
 -> counterfactual
```

without relying on an opaque LLM decision.
