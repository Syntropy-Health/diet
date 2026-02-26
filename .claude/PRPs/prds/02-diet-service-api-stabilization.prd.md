# DIET Service - API Stabilization & Rename

## Problem Statement

The Diet Insight Engine (currently at `apps/diet-insight-engine/`) is the central intelligence service that every other component depends on — Chrome Shrine needs it for personalized food scoring, Syntropy-Journal needs it for diet recommendations, Mobile needs it for check-in analysis. But the service has unstable imports (known package import issues), incomplete error handling, and no versioned API contract. The folder name doesn't reflect its role. Every downstream integration is blocked or fragile until this is solid.

## Evidence

- TODOs in codebase: "Fix symtom_diet_solver package imports"
- Current API has 5 endpoints but no OpenAPI spec published for consumers
- Chrome Shrine and Mobile both need DIET but neither has a stable contract to code against
- Error handling flagged as "needs refinement" in codebase analysis
- Folder named `diet-insight-engine` but product name is "DIET" (Diet Insight Engine Transformer)

## Proposed Solution

Stabilize the DIET service: fix import issues, formalize the API contract with OpenAPI spec, add proper error handling and input validation, rename the directory to `apps/diet/`, and ensure the service can be reliably called by all downstream consumers. This is infrastructure hardening, not new features.

## Key Hypothesis

We believe stabilizing the DIET API contract and fixing known issues will unblock 3+ downstream integrations (Chrome Shrine, Journal, Mobile).
We'll know we're right when all three consumers can make reliable API calls with <1% error rate.

## What We're NOT Building

- New analysis features — stabilizing what exists
- Health metrics integration (prepared for, not built) — future PRD
- User-facing UI — DIET is a backend service
- Authentication/authorization — handled by consuming apps

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| API error rate | <1% on valid requests | Logging / LangSmith |
| Response time (symptom analysis) | <3s p95 | API monitoring |
| OpenAPI spec published | Complete for all endpoints | Spec file exists and validates |
| Downstream integrations unblocked | 3 (Chrome Shrine, Journal, Mobile) | Integration test suite |
| Import issues resolved | 0 broken imports | CI passing |

## Open Questions

- [ ] Should DIET expose an MCP interface in addition to REST for Claude-integrated flows?
- [ ] What's the auth strategy when called from Chrome Shrine (extension) vs Journal (server-to-server)?
- [ ] Rate limiting strategy for beta?
- [ ] Should DIET call Open Diet Data MCP directly or maintain its own nutrition cache?

---

## Users & Context

**Primary User**
- **Who**: Internal service consumers (Chrome Shrine, Syntropy-Journal, Syntropy Mobile)
- **Current behavior**: Some calls work, some fail on import errors; no formal contract
- **Trigger**: Any food analysis, symptom reporting, or product search request
- **Success state**: Reliable, documented API that returns structured responses consistently

**Job to Be Done**
When a consuming service needs dietary intelligence (food ranking, symptom analysis, product search), I want to call a stable, documented API, so I can build features without worrying about upstream breakage.

**Non-Users**
End users never call DIET directly. Wellness SMBs interact through Journal/Chrome Shrine.

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | Fix all broken imports and package resolution | Nothing works without this |
| Must | Publish OpenAPI spec for all endpoints | Consumers need a contract |
| Must | Proper error responses (structured error JSON, HTTP codes) | Debugging and reliability |
| Must | Rename directory to `apps/diet/` and update all references | Consistency with product naming |
| Should | Input validation on all endpoints (Pydantic strict mode) | Prevent garbage-in-garbage-out |
| Should | Health check endpoint with dependency status | Ops visibility |
| Should | Request/response logging with correlation IDs | Debugging across services |
| Could | MCP interface for Claude-integrated flows | Align with Open Diet Data pattern |
| Won't | New analysis features — separate PRDs | Scope discipline |

### MVP Scope

Fix imports, add error handling, publish OpenAPI spec, rename directory. That's it.

### User Flow

1. Consumer reads OpenAPI spec
2. Consumer calls `POST /api/v1/symptoms` with validated payload
3. DIET processes via SDO pipeline (LangGraph)
4. Returns structured response with analysis + recommendations
5. On error: returns structured error with correlation ID

---

## Technical Approach

**Feasibility**: HIGH

**Architecture Notes**
- FastAPI already generates OpenAPI — need to enrich with examples and descriptions
- Pydantic models already exist — need strict mode and better validation
- LangGraph pipeline is functional — just needs error boundaries
- Rename is a git mv + reference updates across monorepo

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Rename breaks submodule references | MEDIUM | Search all configs, CI, imports before rename |
| LangGraph pipeline has hidden failure modes | MEDIUM | Add try/catch at each graph node, structured error propagation |
| OpenAI API rate limits during beta | LOW | Add retry with exponential backoff, queue system |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Fix & rename | Fix imports, rename dir, update references | complete | - | - | [02-diet-service-api-stabilization.plan.md](../plans/02-diet-service-api-stabilization.plan.md) |
| 2 | Error handling | Add structured errors, validation, correlation IDs | complete | - | 1 | [02-diet-service-api-stabilization.plan.md](../plans/02-diet-service-api-stabilization.plan.md) |
| 3 | API contract | Publish OpenAPI spec with examples | complete | with 2 | 1 | [02-diet-service-api-stabilization.plan.md](../plans/02-diet-service-api-stabilization.plan.md) |
| 4 | Integration verification | Test from Chrome Shrine, Journal, Mobile | complete | - | 2, 3 | [02-diet-service-api-stabilization.plan.md](../plans/02-diet-service-api-stabilization.plan.md) |

### Phase Details

**Phase 1: Fix & Rename**
- **Goal**: Clean foundation
- **Scope**: Fix imports, `git mv` to `apps/diet/`, update all cross-references
- **Success signal**: `pytest` passes, all imports resolve

**Phase 2: Error Handling**
- **Goal**: Reliable error responses
- **Scope**: Structured error JSON, HTTP codes, correlation IDs, LangGraph error boundaries
- **Success signal**: No unhandled exceptions in any endpoint

**Phase 3: API Contract**
- **Goal**: Consumers can code against a stable spec
- **Scope**: OpenAPI spec with examples, published at `/docs`
- **Success signal**: Spec validates, matches actual behavior

**Phase 4: Integration Verification**
- **Goal**: Prove downstream services work
- **Scope**: Integration tests from each consumer
- **Success signal**: All 3 consumers making successful calls

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Rename to `diet/` | `apps/diet/` | `apps/diet-insight-engine-transformer/`, keep current | Short, matches "DIET" acronym, clean |
| Error format | RFC 7807 Problem Details | Custom format, plain text | Industry standard, parseable |
| Spec approach | Auto-generate from FastAPI + manual enrichment | Hand-written spec, separate spec repo | Fastest path to accurate spec |

---

## Research Summary

**Market Context**
Every competing platform (Levels, InsideTracker, Viome) has a stable internal API powering their recommendations. Unstable APIs are a common startup failure mode — ship fast but break integrations.

**Technical Context**
- FastAPI at `app/main.py` with existing routers
- SDO pipeline in `diet_insight_engine/sdo/`
- HSA (Health Store Agent) in `diet_insight_engine/health_store_agent/`
- Hydra config in `config/`
- Known import issue in `symtom_diet_solver` package

---

*Generated: 2026-02-25*
*Status: DRAFT - needs validation*
*Priority: P0 - Foundation*
*Master PRD: beta-release-master.prd.md*
