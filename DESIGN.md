# AI Tour Guide — Multi-Agent System (Design Blueprint)

A production-style, fully free multi-agent travel agent: it suggests destinations that
fit a traveler's needs and budget, then plans a complete, grounded, day-wise trip with
real costs in the user's home currency. Works worldwide. Grounded in live search to
avoid hallucination; all arithmetic done in Python, never by the LLM.

---

## 1. Tech stack (all free)

| Layer | Tool |
|---|---|
| Language | Python |
| Orchestration | LangGraph (supervisor + specialists) + LangChain |
| LLM (large) | Groq — `llama-3.3-70b-versatile` (reasoning) |
| LLM (small) | Groq — `llama-3.1-8b-instant` (parsing, extraction) |
| Search / grounding | Tavily (free tier) |
| Hotel data | Tavily search + booking links (primary); Airbnb community MCP (supplement) |
| Currency / FX | Frankfurter (no key) + its MCP server; fawazahmed0 currency-api as fallback |
| RAG (optional) | FAISS + `sentence-transformers` (`all-MiniLM-L6-v2`, local) |
| Structured output | Pydantic |
| Caching | LangChain `SQLiteCache` + local cache for search/FX (with TTL) |
| Observability | LangSmith (free tier) — wired from day one |
| PDF export | ReportLab (Platypus; embed Unicode fonts for non-Latin output) |
| Backend | FastAPI |
| Frontend | Minimal functional page (no marketing chrome) |
| Integration | Expose the agent as an MCP server |
| Package manager | uv |

---

## 2. Agent roster (1 supervisor + 5 specialists, RAG optional 6th)

- **Supervisor** — orchestrator. Mostly deterministic routing with LLM judgment only at
  real decision points (re-suggest? feasible? which agent next?).
- **Intake agent** — validates input, detects home country/currency, disambiguates
  ambiguous place names. *(Mostly deterministic.)*
- **Research agent** — tool-using; chooses/repeats Tavily searches, ranks 3–5 suggestions
  by fit, applies budget feasibility gate. *(Autonomous.)*
- **Route agent** — tool-using; detects direct vs multi-leg (gateway hub), grounds per-leg
  cost. *(Autonomous.)*
- **Planner agent** — tool-using; builds day-wise itinerary, rooming config, hotel options.
  *(Autonomous.)*
- **Budget agent** — converts to home currency, runs all cost math in Python, checks
  budget fit. *(Deterministic.)*
- **RAG agent (optional)** — retrieves from a curated corpus (visa rules, seasonal safety,
  packing, regional tips).

> Honesty note for interviews: describe it as "deterministic specialists plus tool-using
> agents under a supervisor." Don't claim all six are autonomous.

---

## 3. Conversation flow

```
Round 1 questions  ->  Research: suggest 3-5 places (or skip if place-in-mind)
        |                         |
        |                    user selects one  (or: "none of these" -> re-suggest
        |                         |                  / infeasible -> helpful options)
        v                         v
   feasibility gate         Round 2 questions (bus + hotel detail for that place)
                                  |
                                  v
                       Route + Planner + Budget  ->  full plan + PDF
                                  |
                                  v
                       Refinement loop ("cheaper", "swap hotel", "change day 2")
                       -> re-runs only the relevant agent
```

---

## 4. Complete question set

### Round 1 — required core
1. Starting city **and country** (sets origin + home currency)
2. Trip start date
3. Trip end date
4. Number of travelers
5. Who's going — solo / couple / friends / family (with kids?) / colleagues
6. Total budget
7. Budget for whole group or per person?
8. Preferred transport for the main journey — bus / train / flight / car / cheapest / any

### Round 1 — optional (defaulted if skipped)
9. Travel-timing preference (overnight ok / daytime only)
10. Budget strict or flexible?
11. **Max one-way travel time you'll tolerate** *(new)*
12. **Mobility / age constraints** — elderly, toddlers, fitness limits *(new)*
13. **Date flexibility** — fixed or ±1–2 days *(new)*
14. Trip vibe — relax / adventure / nature / spiritual / party / sightseeing / mixed
15. Destination type — mountains / beach / city / offbeat village / wildlife / any
16. Weather — cold / pleasant / hot / snow / doesn't matter
17. Purpose — honeymoon / birthday / family / friends / solo / photography / trek
18. Pace — packed or relaxed
19. Food — veg / non-veg / vegan / both + allergies
20. Special requirements (free text)
21. Preferred output language (default English)
22. Nationality / passport (only for international trips)
23. Place already in mind? (if yes, skip suggestions)

### Round 2 — after a place is selected (rooming + bands)
24. Suggest room split or specify it?
25. If specifying: how many rooms + bed types?
26. Non-couples — okay sharing or separate rooms?
27. Bed preference when sharing — double or twin
28. Property type — hotel / homestay / hostel / resort / any
29. Preferred area / top location
30. Room view — mountain / lake / garden / none
31. Must-have amenities
32. **Local transport comfort at destination** — okay with cabs/scooters or walkable only *(new)*
33. **Transport fare band** — agent shows real range, then asks your max
34. **Hotel per-night band** — agent shows real range, then asks your range

> Conditional logic keeps it short: 24–31 only when relevant, 22 only international,
> 23 can skip the whole suggestion phase.

---

## 5. Core principles

- **Grounding-first**: every fact (places, routes, fares, hotels) comes from live search,
  never from model memory. Temperature 0.
- **Math in Python, never the LLM**: search/LLM supply unit rates; code does all
  multiplication and summation. Totals are always correct.
- **Model tiering**: small model for parsing/extraction, large model for reasoning.
- **Honest uncertainty**: anything unverified is marked "verify before booking" with a
  booking link — never invented.
- **RAG only on a real corpus**: visa/safety/seasonal/packing knowledge, not live search
  wrapped in FAISS.
- **MCP for integration, not tokens**: consume the Frankfurter currency MCP and the Airbnb
  community MCP (hotel supplement); expose the whole agent as an MCP server.

---

## 6. Cost logic (transport + hotel, identical pattern)

1. Show the real grounded range found in search.
2. User picks their band.
3. Suggest options inside the band.
4. **Compute in Python:**
   - Transport total = per-person fare × number of travelers
   - Hotel total = nightly rate × nights × rooms  (nights = checkout − checkin)
5. Display: unit cost on the left, **bold total on the right**.
6. Always state the variance reason (bus type, booking date, season, operator) so the
   number is honest.

**Hotel data source order**: Tavily search + Booking/MakeMyTrip links is the reliable
**primary** (works for budget hotels in small towns). The Airbnb community MCP is layered
on top as a **supplement** for homestays/apartments, and is purely additive — if it fails
or returns nothing, the full Tavily results remain, so the agent never breaks. No free MCP
exists for bus data, so bus stays on Tavily search + booking links.

---

## 7. Routing

- **2-leg norm**: long-haul (user's mode) + last-mile (local cab/bus). Covers ~95% of
  cases (Jibhi: Delhi→Aut bus + Aut→Jibhi cab).
- Transport preference applies to the long-haul; the last mile is whatever's available.
- **3+ transfers**: agent describes the route from search but flags "needs multiple
  transfers — verify locally" instead of forcing structured legs.
- Connectivity + affordability feed back into suggestion ranking.

---

## 8. Output spec

The final plan contains:
- **Budget-fit headline first** — "Total est. ₹11,200 of ₹12,000 — within budget, ₹800 buffer"
- Route broken into legs, each with grounded cost + booking link + map link
- Day-wise itinerary (paced per preference)
- Room configuration(s) + hotel options with per-night and total cost + booking link
- Budget breakdown table, in the user's home currency
- **Tailored packing / what-to-carry list** (RAG-powered, season + place specific)
- Safety notes + any seasonal / route-condition warnings
- **Booking order with urgency** ("book bus now, hotels can wait")
- **Downloadable PDF** — ReportLab Platypus (auto-flow, no overlap), embedded Unicode
  fonts so non-English output renders, clickable links

---

## 9. Robustness & defaults (what keeps it from breaking)

- **Place disambiguation** — confirm region/country for same-name towns.
- **Input validation with reasons** — past dates, origin = destination, unresolvable city,
  end before start → clean stop explaining why.
- **Currency fallback** — if Frankfurter lacks the currency, use fawazahmed0; else show
  local currency with a note.
- **Grounding-failure handling** — reformulate and re-search; if still nothing, say
  "couldn't verify reliably," don't invent.
- **Number sanity checks** — reject implausible extracted fares; prefer min–max ranges.
- **Structured-output retry/repair** — re-prompt with the validation error, or fall back
  to `json_mode` + manual Pydantic parse.
- **Graceful per-agent degradation** — one agent failing returns a partial honest plan,
  not a crash.
- **Runaway caps** — LangGraph `recursion_limit` + max searches per agent.
- **Missing-cost guard** — never multiply a missing value; show "price not found, see link."
- **Per-session isolation** — unique thread_id per session so concurrent users don't collide.
- **Cache TTL** — expire cached fares/FX so stale data doesn't mislead.
- **Re-suggest + infeasibility paths** — "none of these" re-runs research; "over budget"
  returns concrete options (more budget / closer place / fewer nights).

---

## 10. Security

- All Groq/Tavily/FX calls **server-side**; keys never reach the browser.
- Pydantic validation on every request; reject malformed/oversized input.
- Prompt-injection guardrails: agent scoped to travel only; output validated against schema.
- Rate limiting per IP (slowapi); CORS locked to own domain; HTTPS from host.
- Secrets in env vars (never in repo); auto-escaping to prevent XSS; safe errors (no
  stack traces / keys leaked).

---

## 11. Build order

1. Foundation — config, Pydantic schemas, validation, tools (Tavily + Frankfurter),
   caching, model-tiering, LangSmith tracing
2. Intake agent (validation, currency, disambiguation)
3. Research agent (suggestions + feasibility gate)
4. Route agent (multi-leg + per-leg cost)
5. Planner agent (itinerary + rooming + hotels)
6. Budget agent (currency + code math + budget-fit)
7. Supervisor (orchestration, re-suggest/infeasibility, refinement loop)
8. Robustness pass (degradation, caps, retries, defaults)
9. Output layer (plan formatting + PDF with Unicode fonts + links)
10. RAG agent + curated corpus (optional)
11. FastAPI backend + minimal frontend + security
12. MCP server wrapper (expose agent; consume Frankfurter MCP)
13. Eval set (~10 scenarios) + final hardening
