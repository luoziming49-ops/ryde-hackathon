# Ryde Dispute AI

**Multi-Agent Autonomous Dispute Resolution System** — Digital Native Track (Ryde)
· Tencent Cloud × AI Singapore Hackathon 2026

A working prototype that autonomously resolves ride-hailing disputes between riders and
drivers — gathering evidence, building adversarial cases, applying company policy, and issuing
fair rulings with a confidence score and a natural-language explanation.

---

## What it does

Ride-hailing platforms process thousands of dispute tickets daily (route deviations, no-show
charges, fare disputes…). Humans manually review GPS, chat, payment records and policy —
slow (24–72h), costly and inconsistent.

This prototype replaces that with a **multi-agent system**:

| Agent | Type | Role |
|---|---|---|
| **Evidence Collection Agent** | Stretch | Indexes GPS/telemetry, chat, fare and account history into structured evidence. |
| **Rider Advocate Agent** | **Core** | Gathers rider-side evidence, cites policy, argues for a rider-favourable outcome. |
| **Driver Advocate Agent** | **Core** | Gathers driver-side evidence, cites policy, argues for a driver-favourable outcome. |
| **Fraud & Bad-Faith Agent** | Stretch | Scores behavioural dispute-abuse risk for both parties. |
| **Policy & Precedent Agent** | Stretch | Retrieves relevant policy clauses and past rulings (RAG-style) for consistency. |
| **Judge Agent** | **Core** | Weighs both cases, applies policy, issues a ruling with confidence + reasoning. |
| **Escalation Protocol** | Stretch | Escalates to a human reviewer when confidence falls below a threshold. |

The system is **demoable end-to-end for two dispute categories** (route deviation + no-show),
with every inter-agent message rendered in an observable communication log.

---

## Key design principle

> **GenAI produces drafts and arguments — never the final decision alone.**

The correctness-critical layer is **deterministic**:

1. A deterministic **evidence engine** turns raw data into computed facts (deviation %, wait
   time, arrival distance) that cannot be hallucinated.
2. A deterministic **policy engine** applies Ryde's rules to those facts to produce a ruling
   prior.
3. The **agents** (optionally backed by an LLM) generate persuasive, human-readable arguments
   and reasoning *on top of* those facts.
4. The **Judge** starts from the policy prior and adjusts confidence from fraud signals and
   precedent — falling back to human escalation when uncertain.

This means the demo runs with or without an LLM API key, and the architecture is honest,
auditable and safe by construction.

---

## Running it

```bash
cd ryde-dispute-ai
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in a browser.

### Optional: enable a real LLM

The agents automatically use any OpenAI-compatible chat-completion endpoint when a key is
present (Tencent Cloud Hunyuan, OpenAI, etc.). Without it, they fall back to deterministic
template reasoning — everything still works.

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # or your provider
export LLM_MODEL="gpt-4o-mini"                        # or your model
```

The `/api/health` endpoint reports whether the LLM is active.

---

## Demo walkthrough (5 min)

1. Open the app — the top-left lists three sample disputes.
2. Select **RYDE-2026-0001 (route deviation)** and inspect the **Evidence** tabs:
   GPS map (actual vs optimal route), chat log, fare breakdown, party history.
3. Click **⚡ Resolve Dispute** — watch the orchestration log animate through:
   evidence collection → fraud scoring → policy retrieval → rider & driver advocates →
   judge ruling.
4. Read the **Ruling** panel: action, refund amount, confidence gauge, matched policy
   clauses, and the judge's natural-language explanation.
5. Repeat for **RYDE-2026-0002 / -0003 (no-show)** to see opposite outcomes
   (full refund vs fee upheld) driven purely by the evidence.

### The three sample rulings

| Case | Category | Evidence | Ruling | Confidence |
|---|---|---|---|---|
| RYDE-2026-0001 | Route deviation | 43% detour + 6-min stop, no traffic | **Partial refund SGD 7.87** | 96% |
| RYDE-2026-0002 | No-show | Driver never arrived (1.18 km away) | **Full refund SGD 5.00** | 98% |
| RYDE-2026-0003 | No-show | Driver arrived (45 m) & waited 6 min | **No action** (fee upheld) | 95% |

---

## Repository layout

```
ryde-dispute-ai/
├── backend/
│   ├── main.py                 # FastAPI app + REST endpoints
│   ├── agents/
│   │   ├── orchestrator.py     # pipeline coordinator + evidence collection agent
│   │   ├── advocates.py        # Rider / Driver Advocate agents (core)
│   │   ├── judge.py            # Judge agent (core) + escalation protocol
│   │   ├── fraud_detection.py  # Fraud & bad-faith agent (stretch)
│   │   ├── policy_precedent.py # Policy & precedent RAG (stretch)
│   │   └── base.py             # base agent + observable message type
│   └── core/
│       ├── evidence.py         # deterministic evidence analysis
│       ├── policy.py           # deterministic policy engine
│       └── llm.py              # LLM provider + offline fallback
├── frontend/
│   └── index.html              # single-file UI (pipeline log, evidence, ruling)
├── sample_data/
│   ├── disputes.json           # 3 sample dispute cases
│   ├── policies.json           # Ryde policy clauses (versioned)
│   └── precedents.json         # past rulings for consistency
├── docs/
│   └── architecture.svg        # standalone architecture diagram
└── requirements.txt
```

---

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Backend + LLM status |
| GET | `/api/disputes` | List sample disputes |
| GET | `/api/disputes/{id}` | Full case file |
| POST | `/api/resolve` | Run the multi-agent pipeline (`{"case_id": "..."}`) |
| GET | `/api/policies` | Policy knowledge base |
| GET | `/api/precedents` | Precedent knowledge base |

The `/api/resolve` response contains the full **observable trace** (every agent message),
evidence analysis, advocate arguments, fraud signals, and the final ruling.

---

## Stretch goals implemented

- ✅ Evidence Collection Agent (multi-source structured retrieval)
- ✅ Fraud & Bad-Faith Detection Agent (behavioural risk scoring)
- ✅ Policy & Precedent Agent (RAG-style retrieval for ruling consistency)
- ✅ Escalation Protocol (low confidence → human review)
- ✅ Observable inter-agent communication (animated log + API trace)

**Not implemented** (documented as future work): image analysis for property-damage/mess
(multi-modal), the Learning Feedback Loop (human overrides → KB update), and SLA/routing
prioritisation. These are designed into the architecture but intentionally scoped out to keep
the MVP demoable.

---

## Submission checklist (vs. handbook)

| Required item | Status | Where |
|---|---|---|
| Built with CodeBuddy/WorkBuddy | ⬜ You | This project was built via WorkBuddy — keep your chat history as proof |
| Project title | ✅ | **Ryde Dispute AI** |
| Short blurb (<10 words) | ✅ | *"Multi-agent AI judges ride disputes fairly in seconds"* |
| Project description | ✅ | See sections above (overview / pain points / architecture / value) |
| Architecture diagram | ✅ | `docs/architecture.svg` (also in-app under 🗺 Architecture) |
| Cover image 380×216 (16:9) | ✅ | `docs/cover.png` |
| Demo walkthrough | ✅ | README "Demo walkthrough" section |
| Source code (GitHub) | ⬜ You | Push this folder to a GitHub repo |
| Chat history (≥3 screenshots) | ⬜ You | Screenshot your CodeBuddy/WorkBuddy sessions |
| Demo video (optional) | ⬜ You | 5–8 min screen recording following the walkthrough |
| Live URL (bonus) | ⬜ You | Deploy e.g. to Tencent Cloud and submit the URL |

**Quantifiable business value** (for the Project Description): the system resolves standard
disputes autonomously in **< 1 second** vs. the current 24–72 h human process; the three core
agents + policy engine produce **consistent rulings** from identical evidence (removing
inter-agent variance); the escalation protocol guarantees **human review for low-confidence or
safety cases**; and the full observable trace provides a **complete audit trail** per ruling.
