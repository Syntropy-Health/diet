# Chrome Shrine ↔ DIET & Open Diet Data Integration

## Problem Statement

Chrome Shrine is production-ready (v1.0) with food image analysis via GPT-4 Vision and FDA/USDA safety alerts. However, it operates in isolation — it doesn't know the user's dietary profile, can't provide personalized recommendations (how well a food fits YOUR diet), and doesn't query the Open Diet Data for structured nutritional information. The extension's core promise is "personalized pop-up insights while shopping" but personalization requires connecting to DIET (for user profile + ranking) and Open Diet Data (for accurate nutrition data). Currently, it's generic food analysis, not personalized diet intelligence.

## Evidence

- Chrome Shrine has no API calls to DIET service or Open Diet Data MCP
- Current analysis uses GPT-4 Vision with no ground-truth nutrition data
- The extension's value prop requires personalization — generic food info already exists (FoodHealth.co, Sift, FeedBun)
- Market research confirms: no browser extension does personalized supplement/food analysis against user health profile — this is genuine whitespace
- Chrome Shrine already has scraper modules for Amazon Fresh, CookUnity, and generic sites

## Proposed Solution

Connect Chrome Shrine to DIET service for personalized scoring (how well this food fits the user's diet profile) and to Open Diet Data MCP for accurate macronutrient data. The hover-card popup should show: (1) accurate macro breakdown from Open Diet Data, (2) personalized fit score from DIET, (3) existing FDA/USDA safety alerts, (4) actionable recommendation ("good fit for your protein goal" or "high in sugar — you've been over target this week").

## Key Hypothesis

We believe personalized food scoring at the point of online shopping will be a compelling user acquisition and retention driver — users will install and keep the extension because generic food info tools can't tell you "this fits YOUR diet."
We'll know we're right when >40% of active extension users view 10+ food insights per week.

## What We're NOT Building

- In-extension journaling — that's Journal/Mobile's job
- Purchase tracking / cart analysis — future feature
- Supplement stack interaction checking — future
- In-extension user profile editing — managed in Journal

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Personalized insights shown per user per week | >10 | Extension analytics |
| Extension daily active users | >500 in beta | Chrome Web Store analytics |
| User-rated insight relevance | >3.5/5 | In-extension feedback |
| Macro data accuracy (vs manual check) | >90% | QA audit |

## Open Questions

- [ ] How does Chrome Shrine authenticate against DIET? Clerk session token from Journal? Separate extension auth?
- [ ] How to handle DIET latency in a hover-card context? (need <1s for good UX)
- [ ] Should Open Diet Data be queried directly (MCP) or through DIET as intermediary?
- [ ] Offline behavior — what to show when DIET is unreachable?
- [ ] Do we need a local nutrition cache in the extension for speed?

---

## Users & Context

**Primary User**
- **Who**: Biohacker shopping for food/supplements on Amazon, CookUnity, iHerb, etc.
- **Current behavior**: Uses Chrome Shrine for generic food analysis, separately logs in Journal
- **Trigger**: Hovers over or clicks on a food/supplement product while shopping
- **Success state**: Sees a personalized popup: "This has 25g protein. Fits your daily target. Your macro gap: fiber is low today — consider adding [alternative]."

**Job to Be Done**
When I'm shopping for food or supplements online, I want to instantly see how a product fits my personal diet goals, so I can make better purchasing decisions without switching apps.

**Non-Users**
- Users who haven't set up a Syntropy-Journal profile (extension shows generic info as fallback)
- Users on mobile browsers (extension is desktop Chrome only)

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | DIET API integration for personalized food scoring | Core differentiator |
| Must | Open Diet Data query for structured macro breakdown | Accuracy vs LLM approximation |
| Must | Personalized hover-card: macros + fit score + recommendation | User-facing value |
| Must | Fallback to generic analysis when user not authenticated | Don't break current functionality |
| Should | Local nutrition cache for frequently queried foods | Speed (<1s popup) |
| Should | Auth flow linking extension to Syntropy-Journal account | Seamless identity |
| Could | "Add to journal" button on hover-card | Cross-product engagement |
| Could | Weekly shopping summary (what you browsed, macro impact) | Retention feature |
| Won't | In-extension profile editing — managed in Journal | Single source of truth |

### MVP Scope

DIET API call from extension (auth via Clerk token), Open Diet Data macro lookup, updated hover-card showing: food name, macro breakdown, personal fit score (1-10), one-line actionable recommendation. Fallback to current GPT-4 Vision analysis for unauthenticated users.

### User Flow

1. User has Chrome Shrine installed + Syntropy-Journal account
2. Extension authenticates via Clerk session (background service worker)
3. User hovers over food product on Amazon/CookUnity/any site
4. Extension scrapes food info (existing scraper modules)
5. Parallel calls: DIET for personalized score + Open Diet Data for macros
6. Hover-card displays: macros, fit score, recommendation, safety alerts
7. User can click "Add to Journal" to log the food

---

## Technical Approach

**Feasibility**: MEDIUM

**Architecture Notes**
- Chrome Shrine already has modular architecture: scrapers, AI, integrations, UI
- Add new integration modules: `src/modules/integrations/diet-api.ts` and `src/modules/integrations/open-diet-data.ts`
- Auth: Clerk provides JWT tokens; extension service worker can manage tokens via `chrome.identity` or shared cookie
- DIET call: POST to DIET API with food + user profile context → personalized score
- Open Diet Data: Query via HTTP (MCP protocol or a lightweight REST wrapper)
- Caching: IndexedDB in extension for frequently queried foods

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| DIET latency too high for hover-card UX | HIGH | Local cache, show skeleton while loading, pre-fetch on page scan |
| Auth complexity (extension → Clerk → DIET) | MEDIUM | Use Clerk's getToken() in extension context; fallback to generic |
| CORS issues calling DIET from extension | LOW | Extension service worker is not subject to CORS; use background fetch |
| Open Diet Data food matching accuracy | MEDIUM | Fuzzy search + GPT-4 Vision as verification layer |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Auth bridge | Clerk auth from extension to DIET service | pending | - | PRD-02 (DIET stable) | - |
| 2 | Open Diet Data integration | Macro lookup module in extension | pending | with 1 | PRD-01 (macro calc) | - |
| 3 | DIET scoring integration | Personalized food scoring from DIET | pending | - | 1 | - |
| 4 | Hover-card redesign | Updated UI with macros + score + recommendation | pending | - | 2, 3 | - |
| 5 | Caching & performance | IndexedDB cache, pre-fetching, skeleton states | pending | - | 4 | - |

### Phase Details

**Phase 1: Auth Bridge**
- **Goal**: Extension can authenticate against DIET as the logged-in user
- **Scope**: Clerk token management in service worker, DIET auth middleware
- **Success signal**: Authenticated API call from extension to DIET returns user-specific data

**Phase 2: Open Diet Data Integration**
- **Goal**: Accurate macros from real nutrition databases
- **Scope**: New integration module, food name → macro lookup, fallback handling
- **Success signal**: Hover-card shows real macro data for a known food

**Phase 3: DIET Scoring**
- **Goal**: Personalized "how well does this fit your diet" score
- **Scope**: DIET API call with food context, score parsing, recommendation extraction
- **Success signal**: Hover-card shows personalized score and one-line recommendation

**Phase 4: Hover-Card Redesign**
- **Goal**: Updated UI showing all new data
- **Scope**: Redesigned hover-card component with macros, score, recommendation, safety alerts
- **Success signal**: Visually clear, loads in <2s, degrades gracefully

**Phase 5: Caching & Performance**
- **Goal**: Sub-second popup experience for common foods
- **Scope**: IndexedDB caching, page-scan pre-fetching, loading skeleton
- **Success signal**: Cached foods show popup in <500ms

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Auth mechanism | Clerk JWT via service worker | API key, no auth (public) | Personalization requires user identity; Clerk is already the auth system |
| Nutrition data source | Open Diet Data (direct) + DIET (scoring) | DIET wraps all nutrition queries | Separation: data vs intelligence; DIET shouldn't be a data proxy |
| Caching strategy | IndexedDB in extension | localStorage, no cache | IndexedDB handles larger datasets; critical for hover UX speed |
| Fallback for unauthed users | Current GPT-4 Vision analysis (generic) | No fallback (require sign-up) | Don't break existing functionality; use as onboarding funnel |

---

## Research Summary

**Market Context**
- FoodHealth.co Chrome extension supports Amazon, Target, Walmart — generic scoring, no personalization
- Sift flags banned ingredients — safety only, no nutrition intelligence
- FoodLama links grocery accounts — closest to personalization but food-only, no supplements
- No extension combines personalized health profile + structured nutrition data + shopping context

**Technical Context**
- Chrome Shrine scrapers: `src/modules/scraper/` (Amazon Fresh, CookUnity, generic)
- AI module: `src/modules/ai/agent.ts` (GPT-4 Vision orchestration)
- Integrations: `src/modules/integrations/` (FDA, USDA recalls)
- UI: `src/modules/ui/hover-card.ts`
- Service worker: `src/background/service-worker.ts`

---

*Generated: 2026-02-25*
*Status: DRAFT - needs validation*
*Priority: P2 - Satellite / Distribution Tool*
*Depends on: PRD-01 (Open Diet Data Macros), PRD-02 (DIET API)*
*Master PRD: beta-release-master.prd.md*
