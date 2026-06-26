🗺️ AI Tour Guide Agent

A production-grade **multi-agent AI travel planner** built with LangGraph, LangChain, and Groq. It suggests real destinations, plans complete trips with grounded costs, and generates downloadable PDF itineraries — all for free.

> **No hallucination. No fake prices. All math in Python, all facts from live search.**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-green)
![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.3-orange)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)

---

## What It Does

1. **You fill a 7-page form** — origin, dates, travelers, budget, activities, food, accommodation preferences
2. **AI suggests 3-5 destinations** — grounded in live search, with honest pros and cons
3. **You pick one → full trip plan** — route, hotels, day-by-day itinerary, budget breakdown, packing list
4. **Refine conversationally** — "make it cheaper", "swap the hotel", "change day 2"
5. **Download a PDF** — professional, clickable booking links, ready to share

---

## Architecture — 7 Specialist Agents
User Form → Intake Agent → Research Agent (+ Feasibility Loop)

↓

User Picks a Place

↓

Route Agent → Itinerary Agent → Hotel Agent

↓

Budget Agent (Python math) → Finalize Agent

↓

Full Plan + PDF + Refinement Loop

| Agent | Role | Type |
|-------|------|------|
| **Intake** | Validates input, detects home currency, blocks injection | Deterministic |
| **Research** | Searches destinations, ranks by fit, feasibility-checks each one | Tool-using (Tavily) |
| **Feasibility** | Checks travel time, reachability, and budget fit per suggestion | Tool-using (Tavily) |
| **Route** | Multi-leg routing with hub detection, per-leg grounded fares | Tool-using (Tavily) |
| **Itinerary** | Day-wise plan with morning/afternoon/evening activities + food | Tool-using (Tavily) |
| **Hotel** | Real hotel names with prices, room configuration in Python | Tool-using (Tavily) |
| **Budget** | All arithmetic in Python — never the LLM. Currency-aware. | Deterministic |
| **Finalize** | Packing list, safety notes, booking links (multi-site), map link | Tool-using (Tavily) |

---

## Key Design Decisions

### Anti-Hallucination
- **Grounding-first**: Every fact (places, routes, fares, hotels) comes from live Tavily search, never from LLM memory. Temperature set to 0.
- **Math in code**: LLMs are unreliable at arithmetic — all cost calculations (transport × travelers × round trip, nightly × nights × rooms) are pure Python.
- **Honest uncertainty**: Anything unverified is marked "verify before booking" with a booking link — never invented.

### Multi-Agent Reliability
- **Model tiering**: `llama-3.1-8b-instant` for parsing/classification, `llama-3.3-70b-versatile` for reasoning — saves quota, improves speed.
- **Structured output with retry + JSON repair**: Pydantic schemas + automatic `json-repair` fallback for Groq's occasional formatting slips.
- **Graceful degradation**: If one agent fails, the system returns a partial plan with an explanation, not a crash.
- **Runaway caps**: LangGraph `recursion_limit` + max searches per agent prevent infinite loops.

### Smart Routing
- **Feasibility loop**: Each suggested destination is checked for reachability by the user's transport mode + travel time before showing.
- **Hub detection**: Detects when a "direct" bus actually drops at a nearby hub (e.g., Delhi→Jibhi buses drop at Aut, not Jibhi).
- **Per-vehicle vs per-person**: Cab costs are per vehicle (shared by the group), bus costs are per person — the budget handles both correctly.
- **Origin exclusion**: Never suggests the traveler's own city as a destination.

### Timing-Aware Planning
- Night departure = no hotel that first night (you're on the bus), itinerary starts next morning.
- Night return = full activities on the last day before boarding.
- Hotel nights computed correctly from departure/return timing, not just date math.

### Budget Intelligence
- Budget is optional — the agent estimates costs if you don't set one.
- If the plan goes over budget, you can type "make it cheaper" and the agent trims instantly.
- The agent uses the budget to pick mid-range options when affordable, not just the absolute cheapest.

### Search Caching
- Disk-persisted search cache (`.search_cache.json`) with 1-hour TTL prevents cost drift across runs and saves Tavily quota.
- LLM response cache via SQLite prevents duplicate Groq calls.

---

## Tech Stack (All Free)

| Layer | Tool | Cost |
|-------|------|------|
| Language | Python | Free |
| Orchestration | LangGraph + LangChain | Free |
| LLM (large) | Groq — `llama-3.3-70b-versatile` | Free tier |
| LLM (small) | Groq — `llama-3.1-8b-instant` | Free tier |
| Search / grounding | Tavily | Free tier (1000/mo) |
| Currency | Frankfurter API | Free, no key |
| Structured output | Pydantic | Free |
| Caching | SQLiteCache + disk search cache | Free |
| PDF generation | ReportLab (Platypus) | Free |
| UI | Streamlit | Free |
| Package manager | uv | Free |

---

## Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Free API keys: [Groq](https://console.groq.com) + [Tavily](https://tavily.com)

### Install

```bash
git clone https://github.com/mr-basu-singh/AI-Tour-Guide-Agent.git
cd AI-Tour-Guide-Agent
uv init
uv add langgraph langchain langchain-groq langchain-tavily langchain-community python-dotenv pydantic streamlit requests reportlab json-repair
```

### Configure

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key_here
TAVILY_API_KEY=your_tavily_key_here
```

### Run

```bash
uv run streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Project Structure
AI-Tour-Guide-Agent/

├── app.py                    # Streamlit UI (7-page wizard)

├── .env                      # API keys (not committed)

├── .gitignore

├── DESIGN.md                 # Architecture blueprint

├── README.md

├── src/

│   ├── init.py

│   ├── config.py             # LLM clients, caching, structured output retry

│   ├── state.py              # Shared agent state (TypedDict)

│   ├── schemas.py            # Pydantic models for all data

│   ├── safety.py             # Input validation + injection protection

│   ├── pipeline.py           # Phase 1 (suggest) + Phase 2 (plan) runners

│   ├── rooms.py              # Room allocation logic (pure Python)

│   ├── refine.py             # Refinement loop (cheaper/swap/change)

│   ├── agents/

│   │   ├── init.py

│   │   ├── intake.py         # Validates input, detects currency

│   │   ├── research.py       # Suggests destinations + feasibility check

│   │   ├── feasibility.py    # Travel time + budget gate per suggestion

│   │   ├── select.py         # Human-in-the-loop place selection

│   │   ├── route.py          # Multi-leg routing with grounded fares

│   │   ├── itinerary.py      # Day-wise plan with food + activities

│   │   ├── hotel.py          # Hotel search + room configuration

│   │   ├── budget.py         # All cost math in Python

│   │   └── finalize.py       # Packing, safety, booking links, map

│   ├── tools/

│   │   ├── init.py

│   │   ├── search.py         # Tavily wrapper with disk cache

│   │   ├── currency.py       # Frankfurter API + country-to-currency

│   │   └── links.py          # Booking link generators (multi-site)

│   └── output/

│       ├── init.py

│       └── pdf.py            # ReportLab PDF generator

---

## Anti-Hallucination Examples

| Scenario | What a naive agent does | What this agent does |
|----------|------------------------|---------------------|
| Delhi → Jibhi by bus | "Direct bus, ₹899" | "No direct bus. Delhi → Aut by bus (₹498–₹5000), then Aut → Jibhi by cab (~₹1000–₹1200/vehicle)" |
| Hotel price in USD | Shows "$70/night" as ₹70 | Currency-aware floor filters implausible prices; estimates from budget instead |
| 3-day trip to Chennai from UP | Suggests it normally | Feasibility check rejects it (30+ hrs by bus for a 3-day trip) |
| Budget ₹12,000 | Plans ₹5,400 skeleton trip | Uses budget intelligently — better hotel, richer itinerary, 5-7 activities/day |
| User lives in Delhi | Suggests Delhi as destination | Origin exclusion prevents suggesting the traveler's own city |
| "Direct" bus to hill town | Reports it as direct | Detects the real drop point (hub) and shows the last-mile cab leg separately |

---

## How the Budget Works
Transport total = Σ (per-leg cost × travelers × 2)     ← round trip

cab legs: cost × vehicles × 2         ← per vehicle, not per person
Hotel total     = nightly rate × nights × rooms         ← nights adjusted for departure timing
Food            = 400/person/day × travelers × days     ← rough estimate

Local transport = 300/day × days                        ← rough estimate

Buffer          = 10% of subtotal                       ← for surprises
All multiplication done in Python. LLM only supplies the unit rates from search.

---

## Refinement Loop

After getting your plan, type any of these:

| Command | What happens |
|---------|-------------|
| "make it cheaper" | Lowers hotel budget band, re-runs budget math instantly |
| "swap the hotel" | Searches for alternative hotels, re-runs budget |
| "change day 2" | Re-generates itinerary with your feedback |
| "change the place" | Asks you to start over with a new destination |

---

## Worldwide Support

The agent works for any origin country. Currency is auto-detected from the country name:

| Origin | Currency | Symbol |
|--------|----------|--------|
| India | INR | ₹ |
| USA | USD | $ |
| UK | GBP | £ |
| Japan | JPY | ¥ |
| South Korea | KRW | ₩ |
| EU countries | EUR | € |
| + 20 more | ... | ... |

Live exchange rates from the Frankfurter API (European Central Bank data, no API key needed).

---

## Future Roadmap

- [ ] RAG agent with curated visa/safety/packing knowledge base (FAISS + HuggingFace embeddings)
- [ ] Airbnb MCP integration for homestay suggestions
- [ ] Frankfurter MCP server for currency conversion
- [ ] Expose the agent as an MCP server (consumable from Claude/Cursor)
- [ ] FastAPI backend for API access
- [ ] LangSmith tracing for observability
- [ ] Eval set with 10+ test scenarios

---

## Built By

**Kumar Basu Singh** — Agentic AI Developer

- 📧 basueps@gmail.com
- 🔗 GitHub: [mr-basu-singh](https://github.com/mr-basu-singh)
- 🔗 LinkedIn: [kumar-basu-singh](https://www.linkedin.com/in/kumar-basu-singh)

---

## License

MIT