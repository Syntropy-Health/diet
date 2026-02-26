# DIET Service - Diet Insight Engine Transformer

## Overview

DIET is the central intelligence service of the SyntropyHealth ecosystem. It processes health journal entries through the SDO (Symptom-Diet Optimizer) pipeline, generates personalized nutritional recommendations, and delivers actionable insights to users via CDC-driven notifications.

## Problem Statement

The DIET service needs to evolve from a request-response API into an event-driven service that continuously processes health data changes (CDC from PostgreSQL) and proactively delivers insights via webapp notifications, text/SMS, and mobile push. Currently, insights are only generated on explicit API calls. Users miss time-sensitive dietary recommendations because they must actively request analysis.

## Architecture

### Current State (API-Driven)

```
User → Journal App → POST /api/v1/symptoms → SDO Pipeline → Response
                                                    ↓
                                            (in-memory only)
```

### Target State (CDC-Driven + API)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL (Railway)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ journal_entries│ │ health_metrics│ │ user_profiles            │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘  │
│         │                  │                                        │
│         └──────────┬───────┘                                        │
│                    │ WAL (Write-Ahead Log)                           │
└────────────────────┼────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────┐
│              Sequin (CDC - self-hosted on Railway)                  │
│  Captures INSERT/UPDATE → delivers via HTTP push to DIET webhook   │
│  ~$5-10/mo self-hosted  |  Built-in retry + exactly-once delivery  │
└────────────────────┬───────────────────────────────────────────────┘
                     │ HTTP POST (webhook)
                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                    DIET Service (FastAPI)                           │
│                                                                    │
│  ┌──────────────┐   ┌───────────────┐   ┌───────────────────────┐ │
│  │ API Routes   │   │ CDC Webhook   │   │ Scheduled Jobs        │ │
│  │ /api/v1/*    │   │ /webhooks/cdc │   │ (daily digest, etc)   │ │
│  └──────┬───────┘   └──────┬────────┘   └──────────┬────────────┘ │
│         │                  │                        │              │
│         └──────────┬───────┴────────────────────────┘              │
│                    │                                               │
│                    ▼                                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │            SDO Pipeline (Symptom-Diet Optimizer)             │   │
│  │  ┌──────────┐ ┌───────────┐ ┌─────────────┐ ┌───────────┐  │   │
│  │  │ Analyzer │→│ Correlator│→│ Recommender │→│ Classifier│  │   │
│  │  └──────────┘ └───────────┘ └─────────────┘ └─────┬─────┘  │   │
│  └────────────────────────────────────────────────────┼────────┘   │
│                                                       │            │
│                                                       ▼            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │            Notification Router                              │   │
│  │  Routes alerts by severity + user preferences               │   │
│  │  TIPS → in-app only  |  SUGGESTION → in-app + digest        │   │
│  │  ALERT → in-app + SMS + push (immediate)                    │   │
│  └──────────┬──────────────────┬───────────────────┬───────────┘   │
│             │                  │                   │               │
└─────────────┼──────────────────┼───────────────────┼───────────────┘
              │                  │                   │
              ▼                  ▼                   ▼
    ┌──────────────┐  ┌──────────────┐   ┌──────────────────┐
    │ Novu (free)  │  │ Brevo SMS    │   │ FCM Push         │
    │ In-App Notif │  │ (existing)   │   │ (future)         │
    │ 10K/mo free  │  │              │   │                  │
    └──────────────┘  └──────────────┘   └──────────────────┘
```

## Recommended CDC/Notification Stack

Evaluated 20+ tools. Recommendation optimizes for lowest cost, minimal ops, and Python-native integration.

| Layer | Tool | Cost | Why |
|-------|------|------|-----|
| **CDC** | [Sequin](https://sequinstream.com/) | ~$5-10/mo self-hosted on Railway | WAL-based, exactly-once delivery, HTTP push to DIET webhook, backfill support, no Kafka/Debezium complexity |
| **Event Orchestration** | [Inngest](https://inngest.com/) (optional) | Free tier: 50K executions/mo | Python SDK, handles retries/scheduling/fan-out, only needed if business rules get complex |
| **In-App Notifications** | [Novu](https://novu.co/) | Free tier: 10K events/mo | Multi-channel (in-app, email, SMS, push), subscriber preferences, React component library |
| **SMS** | [Brevo](https://brevo.com/) (existing) | Already integrated | Transactional SMS via Novu provider or direct |
| **Push** | Firebase Cloud Messaging | Free | Standard for mobile push, integrate when Syntropy Mobile is ready |

### Alternatives Considered

| Tool | Why Not |
|------|---------|
| Debezium + Kafka | Overkill for beta scale; ops-heavy; >$50/mo for managed Kafka |
| Supabase Realtime | Ties CDC to Supabase ecosystem; we're on Railway PostgreSQL |
| PostgreSQL LISTEN/NOTIFY | At-most-once delivery; no retry/backfill; fine for prototyping |
| Fivetran / Airbyte | Data warehouse ETL tools, not real-time event delivery |
| Airtable | Not a CDC tool; useful for ops dashboards but not this use case |
| Knock / Courier | Similar to Novu but less generous free tier |

## Core Components

### SDO Pipeline (Existing)

The Symptom-Diet Optimizer is the core intelligence engine:

1. **SymptomAnalyzer** - LLM-powered symptom parsing and classification
2. **PatternCorrelator** - Links symptoms to nutritional deficiencies
3. **DietRecommender** - Generates food/supplement recommendations via RAG
4. **AlertClassifier** - Scores severity (TIPS < 0.3, SUGGESTION 0.3-0.7, ALERT >= 0.7)

### Notification System (Existing, In-Memory)

Event types: `SYMPTOM_REPORTED`, `INSIGHT_GENERATED`, `ALERT_TRIGGERED`, `PRODUCT_QUERY`, `PRODUCT_MATCHED`, `RECOMMENDATION_GENERATED`

Handlers: `InAppNotificationHandler`, `PushNotificationHandler`, `EmailNotificationHandler`, `SMSNotificationHandler`

Router dispatches based on alert severity and handler configuration.

### Health Store Agent (Existing)

Product search via adapter pattern: `BaseStoreAdapter` → `AmazonAdapter`, `ShopAdapter`

### Data Sources (via Open Diet Data MCP)

- USDA FoodData Central (900K+ foods)
- OpenNutrition (300K+ foods, barcode lookup)
- NIH DSLD (100K+ supplements, external API)

## Implementation Phases

| # | Phase | Description | Status | Depends |
|---|-------|-------------|--------|---------|
| 1 | API Stabilization | Fix imports, RFC 7807 errors, OpenAPI spec, config-driven | complete | - |
| 2 | Package Rename | `diet_insight_engine` → `diet`, own repo, submodule | complete | 1 |
| 3 | CDC Integration | Sequin setup, webhook handler, event processing | pending | 2 |
| 4 | Notification Delivery | Novu integration, multi-channel routing | pending | 3 |
| 5 | Scheduled Insights | Daily digest, weekly summary, trend detection | pending | 4 |

## Configuration

All configuration is Hydra-driven via `config/`:

```
config/
├── config.yaml          # Main config with defaults
├── app/
│   └── development.yaml # Service name, version, CORS, error handling
├── llm/
│   ├── default.yaml     # LLM provider settings
│   ├── openai.yaml
│   ├── openrouter.yaml
│   └── prompts.yaml     # Prompt templates
├── api/
│   ├── default.yaml     # API defaults
│   └── langsmith.yaml   # Tracing config
├── pipeline/
│   ├── default.yaml     # SDO pipeline config
│   ├── demo.yaml
│   └── meal_planner.yaml
├── logging/
│   ├── development.yaml
│   └── production.yaml
└── prompts/
    ├── default.yaml
    ├── symptom_diet_solver.yaml
    └── symptom_supplement_solver.yaml
```

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| API error rate | <1% on valid requests | Logging / LangSmith |
| Response time (symptom analysis) | <3s p95 | API monitoring |
| CDC event processing latency | <5s from DB write to notification | Sequin + Novu metrics |
| Notification delivery rate | >95% | Novu dashboard |
| Daily active insight engagement | >30% of users | PostHog (PRD-08) |

## Tech Stack

- **Runtime**: Python 3.9+, FastAPI, uvicorn
- **AI/ML**: LangGraph, LangChain, LangSmith (tracing)
- **Config**: Hydra 1.3+ / OmegaConf
- **Logging**: structlog
- **Data**: Open Diet Data MCP (USDA, OpenNutrition, NIH DSLD)
- **CDC**: Sequin (PostgreSQL WAL → HTTP webhook)
- **Notifications**: Novu (multi-channel) + Brevo SMS (existing)
- **Hosting**: Railway

---

*Updated: 2026-02-25*
*Repository: github.com/Syntropy-Health/diet*
*Parent monorepo: github.com/Syntropy-Health/SyntropyHealth (submodule at apps/diet/)*
