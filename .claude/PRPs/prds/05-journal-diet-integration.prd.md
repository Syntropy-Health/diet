# Syntropy-Journal ↔ DIET Service Integration

## Problem Statement

Syntropy-Journal collects diet and health data through journaling but doesn't use the DIET service to transform that data into personalized dietary intelligence. Users log food, symptoms, and supplements but receive no automated analysis of what to eat, what to avoid, or how their current diet ranks against their goals. The DIET service exists and has a functional SDO (Symptom-Diet Optimizer) + HSA (Health Store Agent) pipeline, but it's not wired into the Journal. The core value proposition — actionable diet intelligence — is disconnected from the core data collection point.

## Evidence

- DIET service has working endpoints: POST /api/v1/symptoms, POST /api/v1/products/search
- Syntropy-Journal has journal entry management and background task system
- No integration exists between them — confirmed by codebase analysis
- Users currently log data but get no automated analysis in return
- This is the #1 feature gap blocking the "Health OS" value proposition

## Proposed Solution

Integrate DIET service into Syntropy-Journal's core flow: when users log journal entries (food, symptoms, supplements), automatically trigger DIET analysis in the background and surface results as actionable insight cards on the dashboard. Include "top diets to pick from" recommendations based on user profile + DIET ranking.

## Key Hypothesis

We believe automatically analyzing journal entries through DIET and surfacing diet recommendations will transform Syntropy from a passive journal into an active health intelligence platform.
We'll know we're right when >50% of users who log 3+ entries engage with the returned insights.

## What We're NOT Building

- Manual DIET queries (user doesn't need to "search" — it's automatic)
- Health store product recommendations in Journal (Chrome Shrine's job)
- Custom diet plan builder — DIET ranks existing diets, doesn't create custom ones
- Wearable data integration — separate PRD (Oura)

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Auto-analysis trigger rate | 100% of journal entries with food/symptom data | Backend logs |
| Insight card engagement | >50% of users click/expand insight cards | PostHog |
| Diet recommendation relevance | >3.5/5 user rating | In-app feedback widget |
| Background task success rate | >95% | Task monitoring system |

## Open Questions

- [ ] How many journal entries before DIET has enough data for meaningful analysis?
- [ ] Should insights update in real-time or batch (daily summary)?
- [ ] How to handle DIET service downtime without degrading journal experience?
- [ ] What diet databases/frameworks does DIET rank against? (Mediterranean, Keto, Paleo, custom?)

---

## Users & Context

**Primary User**
- **Who**: Biohacker who logs food and supplements daily
- **Current behavior**: Logs entries in Syntropy-Journal, gets no automated feedback
- **Trigger**: Logs a meal or reports a symptom
- **Success state**: Sees an insight card within minutes: "Based on your entries, your protein intake is 30% below target. Your top matching diets are: [ranked list]"

**Job to Be Done**
When I log my food and symptoms, I want to automatically receive personalized diet analysis, so I can make better food choices without manual research.

**Non-Users**
- Users who only want a blank journal (no AI) — should be able to opt out
- SMB owners (they see aggregate data, not personal analysis)

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | Auto-trigger DIET analysis on journal entry creation | Core loop |
| Must | Insight cards on dashboard (macro gaps, symptom correlations) | Value delivery |
| Must | Top diet recommendations ranked by DIET | Key feature for "Health OS" |
| Must | Background task integration (non-blocking analysis) | UX — don't slow down logging |
| Should | Historical trend analysis (week-over-week) | Retention driver |
| Should | Opt-out toggle for users who want journal-only | Respect preferences |
| Could | Real-time insight streaming via WebSocket | Immediacy |
| Won't | Product recommendations — Chrome Shrine's domain | Clean boundaries |

### MVP Scope

On journal entry save → trigger DIET `/api/v1/symptoms` in background → store result → render insight card on dashboard. Plus "top diets" section calling DIET ranking.

### User Flow

1. User logs journal entry (food, symptoms, supplements)
2. Reflex background task calls DIET POST /api/v1/symptoms
3. DIET returns analysis (symptom correlations, macro gaps, recommendations)
4. Result stored and rendered as insight card on dashboard
5. Dashboard also shows "Top Diets for You" from DIET ranking
6. User clicks insight → sees detail (what to change, why, evidence)

---

## Technical Approach

**Feasibility**: HIGH

**Architecture Notes**
- Syntropy-Journal already has background task system with WebSocket monitoring
- DIET API exists at known endpoints
- Journal entries map cleanly to DIET's SymptomInput model
- Results stored in PostgreSQL, rendered via Reflex components

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| DIET service latency (LLM calls) makes insights slow | MEDIUM | Background task + "analyzing..." placeholder card |
| Journal entry data doesn't map cleanly to DIET input | MEDIUM | Adapter layer that transforms journal entries to SymptomInput |
| DIET downtime degrades journal experience | LOW | Graceful degradation: journal works without DIET; insights show "unavailable" |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Data mapping | Map journal entries to DIET SymptomInput format | pending | - | PRD-02 (DIET stable) | - |
| 2 | Background integration | Trigger DIET on entry save, store results | pending | - | 1 | - |
| 3 | Insight cards UI | Dashboard insight cards with DIET results | pending | with 4 | 2 | - |
| 4 | Diet ranking | "Top diets for you" section | pending | with 3 | 2 | - |
| 5 | Feedback loop | User rating on insights, opt-out toggle | pending | - | 3 | - |

### Phase Details

**Phase 1: Data Mapping**
- **Goal**: Clean adapter between journal and DIET
- **Scope**: Mapping function, unit tests
- **Success signal**: Journal entries correctly transform to SymptomInput

**Phase 2: Background Integration**
- **Goal**: DIET called automatically on every relevant entry
- **Scope**: Background task hook, error handling, result storage
- **Success signal**: Every food/symptom entry triggers DIET, results stored

**Phase 3: Insight Cards UI**
- **Goal**: Users see actionable analysis
- **Scope**: Reflex components for insight cards, dashboard layout
- **Success signal**: Cards render with real DIET data

**Phase 4: Diet Ranking**
- **Goal**: Show personalized diet recommendations
- **Scope**: DIET ranking endpoint call, ranked list component
- **Success signal**: Users see top 3-5 matching diets

**Phase 5: Feedback Loop**
- **Goal**: Measure and improve relevance
- **Scope**: Rating widget, opt-out toggle, PostHog events
- **Success signal**: Feedback data flowing into PostHog

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Integration pattern | Background task (async) | Synchronous call, webhook | Non-blocking; existing task system supports this |
| Insight delivery | Dashboard cards | Email digest, push notification | Simplest first; notification system is separate PRD |
| DIET call trigger | Every journal entry with food/symptom data | Batch daily, manual trigger | Real-time value perception; async means no UX cost |

---

## Research Summary

**Market Context**
- Levels shows real-time metabolic insights from CGM — immediate feedback loop is the killer feature
- InsideTracker surfaces "zones" after blood work — delayed but actionable
- No competitor does real-time journal → diet intelligence transformation

**Technical Context**
- Journal background tasks: `/api/{state_name}/tasks/{client_token}/start/{task_name}`
- DIET endpoints: POST /api/v1/symptoms, POST /api/v1/products/search
- Reflex state system handles async updates to UI via WebSocket
- DIET uses LangGraph for analysis pipeline — 2-5s typical response time

---

*Generated: 2026-02-25*
*Status: DRAFT - needs validation*
*Priority: P1 - Core Value*
*Depends on: PRD-02 (DIET API Stabilization)*
*Master PRD: beta-release-master.prd.md*
