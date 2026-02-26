# Actionable Insights & Notification System

## Problem Statement

Users log diet data and the DIET service analyzes it (per PRD-05), but there's no system to proactively surface time-sensitive, actionable insights to users. Currently, users must open the app and navigate to see any recommendations. Health optimization requires timely nudges — "You haven't had enough protein today," "Your symptom pattern suggests reducing dairy," "Your magnesium levels have been consistently low." Without proactive delivery, the platform is reactive-only, and retention drops because users forget to check.

## Evidence

- No notification system exists in Syntropy-Journal or Mobile
- Diet Insight Engine has a notification module (`diet_insight_engine/notifications/`) with router.py and handlers.py — but it's not connected to any delivery channel
- Competitor Levels sends real-time metabolic alerts via push notification — highest-engagement feature
- Assumption - needs validation: what's the right notification frequency before it becomes annoying?

## Proposed Solution

Build a two-phase notification system: Phase 1 delivers actionable insight cards within the web app (in-app notifications with badges, priority ranking, and actionable CTAs). Phase 2 extends delivery to SMS/text messages for critical insights. Use the existing DIET notification module as the routing backbone.

## Key Hypothesis

We believe proactive actionable insights delivered at the right time will increase user engagement and retention.
We'll know we're right when users who receive 3+ insights per week have >40% higher 2-week retention than those who don't.

## What We're NOT Building

- Email notifications — low engagement for health alerts
- Push notifications for mobile (handled in Syntropy Mobile PRD)
- Marketing notifications / promotions — this is health intelligence only
- AI chatbot for insights — OpenClaw handles conversational interface

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Insight delivery rate | 3+ per active user per week | Backend logs |
| Insight engagement (click/expand) | >30% | PostHog |
| 2-week retention (insight recipients) | >40% higher than control | PostHog cohort |
| SMS opt-in rate (Phase 2) | >25% of active users | Opt-in tracking |

## Open Questions

- [ ] What notification frequency is optimal? Daily digest vs real-time?
- [ ] How to prioritize insights when multiple are generated? (by urgency? novelty?)
- [ ] SMS provider choice for Phase 2? (Twilio, SNS, other)
- [ ] Should insights be AI-generated text or templated from DIET output?
- [ ] How to avoid "alert fatigue" — when do we suppress?

---

## Users & Context

**Primary User**
- **Who**: Active biohacker who logs food/supplements 3+ times per week
- **Current behavior**: Opens app, checks dashboard manually, misses time-sensitive insights
- **Trigger**: Receives a notification badge or text message
- **Success state**: Sees an actionable insight, acts on it (adjusts diet, adds supplement), sees improvement

**Job to Be Done**
When my diet data reveals something I should act on, I want to be notified immediately, so I can make adjustments before the pattern worsens.

**Non-Users**
- Users who opted out of notifications — respect preferences
- SMB owners (they get separate SMB-relevant notifications, not personal diet insights)

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | In-app notification center (badge, list, priority) | Core engagement mechanism |
| Must | Insight cards with actionable CTAs ("Log more protein," "Try this food") | Actionable, not just informational |
| Must | Priority ranking of insights (critical → informational) | Don't overwhelm with noise |
| Must | Notification preferences (frequency, categories, opt-out) | User control |
| Should | SMS delivery for critical insights (Phase 2) | Reach users outside the app |
| Should | Insight history / timeline | Review past insights |
| Could | Smart delivery timing (learn when user is most responsive) | Optimization |
| Could | Aggregated weekly insight digest | Summary for less active users |
| Won't | Email notifications — low engagement channel for health data | Not worth building |
| Won't | Mobile push — Syntropy Mobile handles its own | Clean boundaries |

### MVP Scope

In-app notification center with badge indicator, insight cards from DIET analysis, priority ranking (Critical/High/Medium/Low/Info using existing AlertLevel enum), notification preferences. SMS is Phase 2.

### User Flow

**In-App (Phase 1):**
1. DIET analysis generates insight (from PRD-05 integration)
2. Notification router categorizes and prioritizes
3. Badge appears on dashboard notification icon
4. User clicks → sees prioritized insight list
5. Clicks insight → sees detail + actionable CTA
6. Marks as read / dismisses / acts on CTA

**SMS (Phase 2):**
1. User opts into SMS notifications (settings)
2. Critical insights trigger SMS via provider
3. SMS contains brief insight + link to app for detail
4. Deep link opens insight card in app

---

## Technical Approach

**Feasibility**: HIGH (Phase 1), MEDIUM (Phase 2)

**Architecture Notes**
- DIET already has `notifications/router.py` and `handlers.py` — extend, don't rebuild
- AlertLevel enum (CRITICAL, HIGH, MEDIUM, LOW, INFO) exists in DIET models
- Reflex supports real-time UI updates via WebSocket — perfect for live notification badges
- PostgreSQL table for notification storage and read/unread state
- Phase 2 SMS: Twilio is most common; needs account and phone number

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Notification fatigue / user annoyance | HIGH | Conservative defaults, easy opt-out, smart suppression |
| SMS cost at scale | MEDIUM | Only critical alerts via SMS; rate limit to max 3/week |
| DIET generates low-quality insights | MEDIUM | Quality threshold before notification; user feedback loop |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Notification data model | DB tables, notification types, preference schema | pending | - | PRD-05 | - |
| 2 | In-app notification center | Badge, list, detail view, read/unread | pending | - | 1 | - |
| 3 | DIET → notification routing | Connect DIET analysis output to notification creation | pending | with 2 | 1 | - |
| 4 | Preference management | User settings for frequency, categories, opt-out | pending | - | 2 | - |
| 5 | SMS delivery (Phase 2) | Twilio integration, opt-in flow, rate limiting | pending | - | 4 | - |

### Phase Details

**Phase 1: Data Model**
- **Goal**: Foundation for notification storage
- **Scope**: Notification table (type, priority, content, read status, user_id), Preference table
- **Success signal**: Notifications can be created and queried

**Phase 2: In-App Notification Center**
- **Goal**: Users see and interact with insights in the app
- **Scope**: Badge component, notification list page, detail cards
- **Success signal**: Notifications render in real-time

**Phase 3: DIET → Notification Routing**
- **Goal**: DIET analysis automatically creates notifications
- **Scope**: Hook into DIET notification router, map analysis results to notification payloads
- **Success signal**: Journal entry → DIET analysis → notification appears

**Phase 4: Preference Management**
- **Goal**: User control over notifications
- **Scope**: Settings UI, frequency controls, category toggles
- **Success signal**: Users can adjust preferences, system respects them

**Phase 5: SMS Delivery**
- **Goal**: Reach users outside the app with critical insights
- **Scope**: Twilio integration, opt-in UI, SMS templates, rate limiting
- **Success signal**: Critical insight triggers SMS, user receives within 60s

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Phase 1 channel | In-app only | Start with SMS, email | Lowest friction, no external dependencies |
| Phase 2 channel | SMS via Twilio | Email, push, WhatsApp | Direct, high open rate, Twilio well-documented |
| Notification storage | PostgreSQL table | Redis, in-memory | Persistence needed; already have PostgreSQL |
| Priority system | Use existing DIET AlertLevel enum | Custom priority system | Already defined, consistent across services |

---

## Research Summary

**Market Context**
- Levels' real-time glucose alerts are their highest-engagement feature
- InsideTracker sends "Biomarker Zone Change" alerts when blood results shift
- FoodHealth.co sends weekly digest emails — low engagement reported
- SMS health nudges show 2-3x engagement over email in health app studies

**Technical Context**
- DIET notification module: `diet_insight_engine/notifications/router.py`, `handlers.py`
- AlertLevel enum in `diet_insight_engine/models/shared.py`
- Reflex WebSocket supports real-time UI updates
- Existing background task system can schedule notifications

---

*Generated: 2026-02-25*
*Status: DRAFT - needs validation*
*Priority: P1 - Core Value / Retention*
*Depends on: PRD-05 (Journal ↔ DIET Integration)*
*Master PRD: beta-release-master.prd.md*
