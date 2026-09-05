# AgentResolve — AI Transaction Forensics

> **The agent makes the transaction. AgentResolve investigates the transaction.**

AgentResolve is an evidence-first forensic workstation for disputes arising from AI-agent commerce. It reconstructs the transaction lifecycle, identifies what happened, evaluates the original deterministic fault rules, and produces an auditable attribution and counterfactual without asking an LLM to decide fault.

## What makes it different

AgentResolve separates four questions:

```text
INCIDENT
What happened?

ATTRIBUTION
What does the recorded evidence support as the cause?

ECONOMIC HARM
What direct financial impact is recorded?

PREVENTABILITY
Could the problem have been caught before the relevant action?
```

## End-to-end flow

```text
Natural-language request
 -> Shopping Agent
 -> Execution trace
 -> Authorization
 -> Checkout / Payment
 -> Fulfillment / Delivery / Refund
 -> Dispute
 -> Evidence reconstruction
 -> Incident
 -> Deterministic attribution
 -> Preventability
 -> Counterfactual
 -> Forensic report
```

The shopping and merchant flows are controlled deterministic simulations. They do not move real money or claim external notarization.

## Canonical fault taxonomy

The original six categories remain stable:

- `USER_AMBIGUITY`
- `AGENT_MISJUDGMENT`
- `MERCHANT_DATA_ERROR`
- `EXTERNAL_CHANGE`
- `USER_POST_PURCHASE_CHANGE`
- `NO_FAULT_DETECTED`

`INSUFFICIENT_EVIDENCE` is a report state, not a fault category.

## Operational incidents

The incident layer supports realistic commerce problems including unauthorized transactions, incorrect amounts, wrong merchants, wrong variants, non-delivery, defects, fulfillment errors, refund failures, payment uncertainty, authorization scope problems, inventory races, fee/tax surprises, promotion failures, duplicate charges and system integration mismatches.

## Forensic evidence

New evidence can carry:

```text
evidence ID
event ID
source
capture method
timestamp
content hash
parent hash
integrity status
```

Agent validation is derived from recorded execution events when those events exist. The legacy validation checklist is retained only for backward compatibility with the original benchmark.

## Dashboard

The Streamlit interface is intentionally compact and forensic rather than chart-heavy. It includes:

- executive overview
- natural-language Shopping Agent
- investigation workstation
- visual request/listing/checkout/delivery diff
- validation black box
- chronological evidence timeline
- rule ledger
- provenance view
- counterfactual replay
- evaluation
- printable forensic evidence packet

## Evaluation

The existing 20-case development + 10-case holdout corpus is preserved as a synthetic deterministic regression/invariant suite. A 100% result on this corpus demonstrates internal consistency under the authored cases; it is not a claim of universal real-world accuracy.

Run:

```bash
pytest
python -m evaluation.evaluate
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
streamlit run dashboard/app.py
```

See `rules.md`, `IMPLEMENTATION_PLAN.md`, and `docs/architecture.md` for the implementation contract and architecture.
