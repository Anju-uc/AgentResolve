# ◈ AgentResolve — AI Transaction Forensics

> **The agent makes the transaction. AgentResolve investigates the transaction.**

AgentResolve is an **evidence-first transaction-forensics platform for AI-agent commerce**.

When an AI agent purchases something on behalf of a user and the transaction is later disputed, AgentResolve reconstructs the **recorded transaction lifecycle** and determines:

- What happened?
- What operational incident occurred?
- What does the recorded evidence support as the cause?
- Could the issue have been prevented?
- What direct economic harm is recorded?
- What would a hypothetical preventative action have changed?

**The deterministic forensic engine makes the decision. The optional LLM only explains it.**

---

## 🎯 The Problem

AI-agent commerce introduces a new class of transaction disputes.

An AI agent can interpret a user's request, search for products, make decisions, validate constraints, and complete a purchase. When that transaction is disputed later, a simple payment record may not explain the full decision context.

A serious investigation may need to reconstruct:

- What the user originally requested
- What the agent interpreted
- What constraints were available to the agent
- What the agent validated before purchase
- What the merchant advertised
- What happened at checkout
- What was fulfilled or delivered
- What changed after purchase
- What evidence supports each conclusion
- Whether the issue could have been prevented

The central question is therefore not simply:

> **"What went wrong?"**

It is:

> **"What does the recorded transaction evidence establish about what happened and what caused it?"**

AgentResolve is designed around that distinction.

---

## 🧠 What AgentResolve Does

AgentResolve treats a disputed AI-agent transaction as a **forensic investigation**, not just a classification problem.

It takes the recorded transaction evidence and processes it through a deterministic investigation pipeline.

The system separates four questions that are often incorrectly combined.

### 1. Operational Incident

**What actually went wrong during the transaction lifecycle?**

Examples include:

- Wrong merchant or payee
- Quantity mismatch
- Variant mismatch
- Price or fee mismatch
- Fulfillment problem
- Payment issue
- Inventory or availability race
- Unauthorized transaction
- Duplicate charge
- Other supported transaction incidents

### 2. Canonical Attribution

**What does the available evidence support as the underlying cause?**

AgentResolve uses a controlled attribution taxonomy:

- `USER_AMBIGUITY`
- `AGENT_MISJUDGMENT`
- `MERCHANT_DATA_ERROR`
- `EXTERNAL_CHANGE`
- `USER_POST_PURCHASE_CHANGE`
- `NO_FAULT_DETECTED`

When the evidence is not strong enough to support a causal conclusion, AgentResolve can return:

- `INSUFFICIENT_EVIDENCE`

This is treated as an evidence status rather than a fault category.

### 3. Economic Harm

**What direct economic impact is recorded?**

AgentResolve keeps financial harm separate from fault attribution.

A transaction can have financial impact without proving who was responsible for it.

### 4. Preventability

**Could the identified issue reasonably have been prevented using the information and controls available at the relevant decision point?**

This allows the investigation to distinguish:

- What happened
- What the evidence points to as the cause
- What harm was recorded
- Whether a preventative control could have changed the outcome

---

## 🔎 Evidence-First Investigation

AgentResolve is built around the principle that **important forensic conclusions should be traceable to recorded evidence**.

Evidence can include:

- User requests
- Agent execution traces
- Product and merchant data
- Validation results
- Authorization information
- Payment events
- Checkout records
- Fulfillment records
- Delivery information
- Post-purchase changes
- Transaction lifecycle events
- Evidence metadata and provenance

Rather than simply returning a label, the system preserves the reasoning path used to arrive at the finding.

The goal is a **defensible finding chain**:

> **Recorded evidence → observed incident → deterministic rule → attribution → preventability → economic impact**

---

## 🧾 Evidence Provenance

AgentResolve treats evidence provenance as part of the investigation.

Recorded evidence can contain information such as:

- Evidence identifier
- Event identifier
- Source and provenance metadata
- Timestamp
- Content hash
- Parent hash
- Integrity status

Integrity can be represented as:

- `VERIFIED`
- `UNVERIFIED`
- `INVALID`

This allows investigators to distinguish between evidence that is structurally supported and evidence whose integrity cannot be established.

---

## 🤖 Agent Execution Trace

The agent's recorded execution trace is an important part of the forensic record.

It can capture the sequence of actions and validations performed during the transaction.

This helps answer questions such as:

- What did the agent know at the time?
- What did it validate?
- Which constraints were checked?
- What information was available before purchase?
- Did the agent skip a required validation?
- Did the recorded action sequence differ from the expected control path?

For compatibility with earlier transaction records, legacy validation information can also be retained where applicable.

The investigation therefore evaluates the **recorded decision context**, rather than pretending to reconstruct information that was never captured.

---

## ⚙️ Deterministic Forensic Engine

The core analysis is deterministic.

AgentResolve does not ask an LLM to decide whether the user, agent, merchant, or an external event caused the dispute.

Instead, the forensic engine applies explicit rules to the recorded evidence.

The investigation follows a controlled processing sequence:

1. Validate the transaction evidence
2. Reconstruct the recorded transaction lifecycle
3. Identify operational incidents
4. Apply canonical attribution rules
5. Calculate attribution scoring
6. Evaluate preventability
7. Estimate recorded economic harm
8. Generate a structured forensic finding
9. Optionally produce a natural-language explanation

This makes the core decision path reproducible.

Running the same evidence through the same deterministic rules should produce the same forensic result.

---

## 🧩 Rule-Based Attribution

The attribution engine is deliberately constrained.

It evaluates evidence against explicit rules rather than relying on model intuition.

### User Ambiguity

The original request does not contain enough information to establish an unambiguous requirement, and the available evidence cannot support a stronger causal conclusion.

### Agent Misjudgment

The agent had the information or constraints necessary to make the correct decision but selected an inconsistent option or failed to perform a required control.

### Merchant Data Error

The merchant-side information used in the transaction was incorrect, inconsistent, or materially different from the recorded transaction facts.

### External Change

A relevant condition changed after the decision in a way that was not reasonably available to the agent at decision time.

### User Post-Purchase Change

The user changed an externally controlled condition after purchase, producing a later dispute.

### No Fault Detected

The recorded evidence does not establish a supported fault category.

### Insufficient Evidence

There is not enough reliable evidence to justify a causal attribution.

This separation helps prevent the common mistake of forcing every disputed transaction into a fault category even when the evidence does not support one.

---

## 🛡️ Preventability Analysis

A fault finding alone does not answer whether the outcome could have been avoided.

AgentResolve therefore evaluates preventability separately.

The investigation can consider whether:

- A relevant validation was available
- The agent performed the validation
- A required control was skipped
- The necessary information existed at the decision point
- A preventative action could reasonably have changed the outcome

Preventability is therefore based on the **decision context that was actually recorded**, not on hindsight.

---

## 🔁 Counterfactual Replay

AgentResolve supports a controlled counterfactual analysis.

This asks:

> **"What would have happened if the relevant preventative action had been taken?"**

The counterfactual is explicitly treated as **hypothetical**.

It is not presented as historical evidence and does not rewrite the original transaction record.

This distinction is important because a forensic investigation must separate:

- What actually happened
- What the evidence establishes
- What might have happened under a different decision path

---

## 💰 Economic Harm

AgentResolve records economic impact independently from causal attribution.

Depending on the transaction evidence, this can include:

- Transaction amount
- Price differences
- Fees
- Refunds
- Other recorded direct financial effects supported by the transaction evidence

The purpose is to answer:

> **"What direct economic impact is actually recorded?"**

rather than assuming that the existence of financial harm proves fault.

---

## 📉 Dispute Drift

AgentResolve can also use post-purchase changes as supporting evidence.

For example, a later transaction state may differ from the original recorded state.

This can help identify changes between:

- Original transaction state
- Later dispute state
- Fulfillment state
- Post-purchase state

Dispute drift is treated as a **supporting forensic signal**, not as a standalone causal verdict.

---

## 🤖 LLM Boundary

The LLM is intentionally kept outside the core decision boundary.

The deterministic engine decides:

- Incident classification
- Attribution
- Evidence sufficiency
- Attribution score
- Preventability
- Economic impact
- Counterfactual result

The LLM is used only where natural-language generation is useful.

Its role is to explain an already-determined forensic result in a clearer human-readable form.

The LLM must not:

- Invent evidence
- Change the canonical fault
- Recalculate the score
- Override deterministic rules
- Create missing facts
- Decide whether evidence is valid
- Convert uncertainty into certainty

This keeps the system **evidence-first and decision-auditable**.

---

## 🖥️ Forensic Investigation Dashboard

AgentResolve includes a Streamlit-based forensic workstation for investigating transactions.

The dashboard is designed to expose the evidence and decision path rather than hide everything behind a single AI answer.

An investigator can inspect areas such as:

- Transaction search
- Transaction state
- Evidence comparison
- Validation results
- Transaction lifecycle
- Incident findings
- Rule evaluation
- Evidence provenance
- Attribution
- Preventability
- Economic harm
- Counterfactual analysis
- Generated forensic explanations
- Evidence packet generation

The interface is intended to make the result explainable and auditable.

---

## 📄 Forensic Evidence Packets

AgentResolve can generate a structured forensic report and PDF evidence packet.

The report brings together the important parts of the investigation, including:

- Transaction summary
- Incident finding
- Attribution
- Evidence
- Rule results
- Preventability
- Economic impact
- Counterfactual analysis
- Supporting transaction information

The purpose is to provide a human-readable investigation artifact rather than only an API response.

---

## 🔬 Evaluation

AgentResolve includes a deterministic synthetic evaluation framework designed to test the forensic engine.

The current evaluation corpus contains:

| Dataset | Cases | Purpose |
|---|---:|---|
| Development | 20 | Development and regression testing |
| Holdout | 10 | Independent validation against unseen synthetic cases |
| Adversarial | 6 | Robustness against difficult and conflicting evidence scenarios |

The evaluator reports:

- Accuracy
- Macro precision
- Macro recall
- Macro F1
- Confusion matrix

The adversarial suite is intended to test cases where evidence can be incomplete, conflicting, or deliberately challenging.

These results are **synthetic regression results**, not claims of production-world fraud detection accuracy.

---

## 🧪 Testing

AgentResolve includes automated tests covering the deterministic forensic pipeline.

The test suite covers areas including:

- Transaction models
- Incident detection
- Attribution rules
- Evidence handling
- Provenance
- Scoring
- Preventability
- Counterfactual analysis
- Simulation
- API behaviour
- Reporting components

The project includes automated regression tests and deterministic evaluation cases for validating the core investigation pipeline.

---

## 🏗️ Architecture

AgentResolve follows a deliberately simple architecture.

The project is organized into a few clear layers:

**Transaction & Simulation Layer**

Creates controlled transaction scenarios and captures the agent's recorded execution trace.

↓

**Evidence & Model Layer**

Represents transactions, lifecycle events, evidence, provenance, and investigation data.

↓

**Deterministic Forensic Engine**

Identifies incidents, applies attribution rules, calculates scores, evaluates preventability, analyzes counterfactuals, and records economic impact.

↓

**Explanation & Reporting Layer**

Turns the deterministic result into a human-readable explanation and forensic evidence packet.

↓

**API & Dashboard**

Provides programmatic access and a visual investigation workstation.

There are deliberately **no unnecessary microservices, queues, or production-scale infrastructure requirements** in the current design.

The architecture is optimized for:

- Determinism
- Auditability
- Reproducibility
- Explainability
- Clear separation of responsibilities

---

## 🗂️ Project Structure

```text
AgentResolve/
│
├── agent/
│   └── simulator.py
│
├── api/
│   └── routes.py
│
├── app/
│   ├── engine/
│   │   ├── analyzer.py
│   │   ├── counterfactual.py
│   │   ├── drift.py
│   │   ├── evidence_score.py
│   │   ├── helpers.py
│   │   ├── incidents.py
│   │   ├── preventability.py
│   │   ├── provenance.py
│   │   ├── rules.py
│   │   └── scoring.py
│   │
│   ├── llm/
│   │   └── explainer.py
│   │
│   ├── models/
│   │   ├── result.py
│   │   └── transaction.py
│   │
│   └── reports/
│       ├── pdf_packet.py
│       └── report_builder.py
│
├── dashboard/
│   └── app.py
│
├── data/
│
├── docs/
│
├── evaluation/
│   └── evaluate.py
│
├── merchant/
│
├── tests/
│
├── .env.example
├── .gitignore
├── IMPLEMENTATION_PLAN.md
├── pytest.ini
├── README.md
├── requirements.txt
└── rules.md
🚀 Quick Start
1. Clone the repository
git clone https://github.com/Anju-uc/AgentResolve.git
cd AgentResolve
2. Create a virtual environment
Windows
python -m venv .venv
.venv\Scripts\activate
Linux / macOS
python -m venv .venv
source .venv/bin/activate
3. Install dependencies
pip install -r requirements.txt
4. Configure environment variables

Copy the example environment file.

Windows
copy .env.example .env
Linux / macOS
cp .env.example .env

Add any required configuration values to .env.

▶️ Run the API

Start the FastAPI application with:

uvicorn api.routes:app --reload

The API provides endpoints for transaction execution, forensic analysis, and related application functionality.

🖥️ Run the Dashboard

Start the Streamlit investigation workstation with:

streamlit run dashboard/app.py

The dashboard can then be used to inspect transaction evidence and review generated forensic findings.

🧪 Run the Tests

Run the automated test suite:

pytest

Run the evaluation suite:

python evaluation/evaluate.py
🔄 Typical Investigation Flow

A typical AgentResolve investigation looks like this:

1. A user provides a purchase request

↓

2. The AI agent interprets the request

↓

3. The agent searches and evaluates available options

↓

4. Constraints and transaction conditions are validated

↓

5. The purchase is executed in the controlled simulation

↓

6. The transaction lifecycle is recorded

↓

7. A dispute or inconsistency is introduced

↓

8. AgentResolve reconstructs the recorded evidence

↓

9. The deterministic engine identifies the operational incident

↓

10. Attribution rules evaluate the supported cause

↓

11. Preventability and economic impact are evaluated

↓

12. A forensic result and evidence packet are produced

The important property is that the final finding remains connected to the recorded transaction evidence.

💡 What Makes AgentResolve Different

AgentResolve is not primarily designed as a generic fraud classifier.

Its focus is transaction reconstruction and forensic attribution for AI-agent commerce.

The project deliberately combines:

Evidence-First Reasoning

Conclusions are grounded in recorded transaction evidence.

Deterministic Attribution

The core fault decision is made using explicit rules rather than probabilistic LLM reasoning.

Operational and Causal Separation

The system first identifies what went wrong operationally and then evaluates what caused it.

Evidence Sufficiency

The system does not force unsupported evidence into a confident fault classification.

Preventability

The investigation asks whether the issue could have been avoided using the information available at the time.

Counterfactual Analysis

The system can evaluate a hypothetical preventative action without confusing it with historical evidence.

Explainable AI Integration

The LLM is used to explain a deterministic result rather than determine the result.

Together, these properties make AgentResolve closer to a forensic investigation system than a conventional AI prediction pipeline.

🧑‍💻 Technology Stack
Backend
Python
FastAPI
Pydantic
Investigation Engine
Deterministic Python rules
Evidence scoring
Attribution scoring
Preventability analysis
Counterfactual analysis
Provenance validation
AI
Optional LLM explanation layer
Deterministic engine remains authoritative
Dashboard
Streamlit
Reporting
Structured report generation
PDF evidence packets
Testing & Evaluation
Pytest
Synthetic development corpus
Synthetic holdout corpus
Adversarial regression corpus
📚 Documentation

The repository includes additional technical documentation.

rules.md

The implementation contract for the forensic engine.

It defines:

Canonical attribution categories
Incident taxonomy
Evidence requirements
Deterministic processing rules
Provenance expectations
Scoring behaviour
Preventability logic
Counterfactual rules
LLM boundaries
Dashboard requirements
Safety and scope constraints
IMPLEMENTATION_PLAN.md

Describes the implementation architecture, development plan, testing strategy, evaluation corpus, and definition of done.

These documents make the implementation and design decisions inspectable beyond the README.

🔐 Safety & Scope

AgentResolve is currently a controlled transaction-forensics simulation.

It is not presented as:

A live payment-processing system
A real-money transaction platform
A real chargeback adjudication service
A legal-liability engine
An official payment-network compliance system
A production fraud-detection system
An external notarization service

The project focuses on demonstrating how AI-agent transaction evidence can be reconstructed and analyzed in a deterministic and auditable way.

🏆 Razorpay AI Buildathon

AgentResolve was designed for the AI Risk Manager problem space of the Razorpay AI Buildathon.

The project focuses on a central challenge created by agentic commerce:

When an AI agent completes a purchase on behalf of a user, how can a later investigator reconstruct the recorded transaction and determine what the available evidence actually supports?

AgentResolve addresses that challenge through:

Transaction reconstruction + evidence provenance + deterministic incident detection + canonical attribution + preventability + economic impact + explainable reporting

The central design principle is simple:

The AI may make the transaction. The investigation should still be able to explain the transaction.

⚠️ Disclaimer

AgentResolve is a research and buildathon prototype demonstrating evidence-first transaction forensics in a controlled environment.

Its findings are based only on the transaction evidence and deterministic rules available to the system.

It should not be interpreted as:

Legal advice
Financial advice
A binding dispute decision
Proof of real-world liability
A production fraud-detection benchmark
An official payment-network determination
📌 Core Principle

AgentResolve is built around one idea:

A disputed AI-agent transaction should be investigated from evidence, not guessed from the final outcome.

The system therefore keeps the investigation chain visible:

Evidence → Incident → Attribution → Preventability → Economic Impact → Explanation

That is the foundation of AgentResolve.

