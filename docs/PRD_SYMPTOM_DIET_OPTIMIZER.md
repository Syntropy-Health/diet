# Product Requirements Document: Syntropy Dieton Symptom-Diet Optimizer (SDO)

## Executive Summary

The **Syntropy Dieton Symptom-Diet Optimizer (SDO)** is an event-driven health insight system that processes asynchronously reported symptoms, generates real-time actionable insights, and delivers tiered notifications to users. The system integrates with health stores via a pluggable **Health Store Agent (HSA)** ingress layer, enabling seamless product recommendations from multiple vendors.

---

## System Architecture Overview

```mermaid
flowchart TB
    subgraph UserLayer["User Interface Layer"]
        UI[/"User Reports Symptom"/]
        NOTIFY[/"Push Notification"/]
    end

    subgraph EventBus["Event Bus (Async Message Queue)"]
        SYMPTOM_EVENT[["SymptomReportedEvent"]]
        INSIGHT_EVENT[["InsightGeneratedEvent"]]
        ALERT_EVENT[["AlertTriggeredEvent"]]
        PRODUCT_EVENT[["ProductMatchedEvent"]]
    end

    subgraph SDO["Symptom-Diet Optimizer (SDO)"]
        direction TB
        INGEST["Symptom Ingestion Service"]
        ANALYZER["LLM Symptom Analyzer"]
        CORRELATOR["Pattern Correlator"]
        RECOMMENDER["Diet Recommendation Engine"]
        ALERT_ENGINE["Alert Classification Engine"]
    end

    subgraph HSA["Health Store Agent (HSA) - Ingress"]
        direction TB
        STORE_FACTORY["Store Factory"]
        SHOP_ADAPTER["Shop Adapter (PoC)"]
        AMAZON_ADAPTER["Amazon Adapter"]
        GENERIC_ADAPTER["Generic Store Adapter"]
        PRODUCT_NORMALIZER["Product Normalizer"]
        VECTOR_DB[("Vector DB\n(Standardized Health Units)")]
    end

    subgraph NotificationService["Notification Service"]
        ALERT_ROUTER["Alert Router"]
        TIPS["💡 Tips (Low)"]
        SUGGESTIONS["📋 Suggestions (Medium)"]
        ALERTS["🚨 Alerts (High)"]
    end

    UI -->|async| SYMPTOM_EVENT
    SYMPTOM_EVENT --> INGEST
    INGEST --> ANALYZER
    ANALYZER --> CORRELATOR
    CORRELATOR --> INSIGHT_EVENT
    INSIGHT_EVENT --> RECOMMENDER
    RECOMMENDER --> ALERT_ENGINE
    ALERT_ENGINE --> ALERT_EVENT
    ALERT_EVENT --> ALERT_ROUTER
    ALERT_ROUTER --> TIPS & SUGGESTIONS & ALERTS
    TIPS & SUGGESTIONS & ALERTS --> NOTIFY

    RECOMMENDER -->|product query| PRODUCT_EVENT
    PRODUCT_EVENT --> STORE_FACTORY
    STORE_FACTORY --> SHOP_ADAPTER & AMAZON_ADAPTER & GENERIC_ADAPTER
    SHOP_ADAPTER & AMAZON_ADAPTER & GENERIC_ADAPTER --> PRODUCT_NORMALIZER
    PRODUCT_NORMALIZER --> VECTOR_DB
    VECTOR_DB -->|matched products| RECOMMENDER
```

---

## Event-Driven Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant EventBus
    participant SDO as Symptom-Diet Optimizer
    participant HSA as Health Store Agent
    participant VectorDB
    participant NotificationSvc

    User->>EventBus: SymptomReportedEvent
    activate EventBus
    EventBus->>SDO: Consume Event
    deactivate EventBus

    activate SDO
    SDO->>SDO: Parse & Validate Symptom
    SDO->>SDO: LLM Analysis (Batch/Stream)
    SDO->>SDO: Pattern Correlation
    SDO->>EventBus: InsightGeneratedEvent
    deactivate SDO

    activate SDO
    SDO->>SDO: Generate Recommendations
    SDO->>EventBus: ProductQueryEvent
    deactivate SDO

    EventBus->>HSA: Consume ProductQueryEvent
    activate HSA
    HSA->>HSA: Route to Store Adapter
    HSA->>VectorDB: Semantic Search
    VectorDB-->>HSA: Matched Products
    HSA->>HSA: Normalize to Health Units
    HSA->>EventBus: ProductMatchedEvent
    deactivate HSA

    EventBus->>SDO: Consume ProductMatchedEvent
    activate SDO
    SDO->>SDO: Classify Alert Level
    SDO->>EventBus: AlertTriggeredEvent
    deactivate SDO

    EventBus->>NotificationSvc: Consume AlertTriggeredEvent
    activate NotificationSvc
    NotificationSvc->>NotificationSvc: Route by AlertLevel
    NotificationSvc->>User: Push Notification
    deactivate NotificationSvc
```

---

## Component Specifications

### 1. Symptom-Diet Optimizer (SDO)

**Purpose**: Core engine that ingests symptoms, performs LLM-powered analysis, correlates patterns, and generates dietary recommendations with alert classifications.

**Capabilities**:
| Capability | Description |
|------------|-------------|
| `symptom_ingestion` | Async event consumer for user-reported symptoms |
| `llm_batch_analysis` | Batch processing of symptoms with streaming LLM |
| `pattern_correlation` | Historical pattern matching across user data |
| `deficiency_detection` | Identify nutritional deficiencies from symptoms |
| `recommendation_engine` | Generate personalized diet/supplement recommendations |
| `alert_classification` | Classify insights into TIPS/SUGGESTION/ALERT levels |

**Key Models**:
- `SymptomEvent` - Incoming symptom report
- `InsightResult` - Analyzed insight with confidence scores
- `DietRecommendation` - Actionable dietary suggestion
- `AlertNotification` - Tiered notification payload

### 2. Health Store Agent (HSA) - Ingress Layer

**Purpose**: Pluggable ingress abstraction that integrates any health/wellness store into the system, normalizing products into standardized health units for vector storage.

**Factory Pattern**:
```mermaid
classDiagram
    class HealthStoreFactory {
        +create_adapter(store_type: StoreType) AbstractStoreAdapter
        +register_adapter(store_type, adapter_class)
        +list_available_stores() List[StoreType]
    }

    class AbstractStoreAdapter {
        <<abstract>>
        +search_products(query: ProductQuery) List[RawProduct]
        +get_product_details(product_id: str) RawProduct
        +normalize_product(raw: RawProduct) StandardizedHealthUnit
    }

    class ShopStoreAdapter {
        +search_products(query: ProductQuery) List[RawProduct]
        +get_product_details(product_id: str) RawProduct
        +normalize_product(raw: RawProduct) StandardizedHealthUnit
    }

    class AmazonStoreAdapter {
        +search_products(query: ProductQuery) List[RawProduct]
        +get_product_details(product_id: str) RawProduct
        +normalize_product(raw: RawProduct) StandardizedHealthUnit
    }

    class StandardizedHealthUnit {
        +product_id: str
        +name: str
        +category: HealthCategory
        +nutrients: Dict[str, NutrientValue]
        +health_claims: List[str]
        +embedding: List[float]
    }

    HealthStoreFactory --> AbstractStoreAdapter
    AbstractStoreAdapter <|-- ShopStoreAdapter
    AbstractStoreAdapter <|-- AmazonStoreAdapter
```

### 3. Alert Classification System

**Alert Levels**:
| Level | Type | Trigger Condition | Action |
|-------|------|-------------------|--------|
| LOW | TIPS | General wellness insights | Passive notification |
| MEDIUM | SUGGESTION | Detected pattern requiring attention | Active notification with recommendations |
| HIGH | ALERT | Critical health indicator detected | Immediate notification with urgent action |

**Classification Logic**:
```mermaid
flowchart LR
    INPUT[Insight Result] --> SEVERITY{Severity Score}
    SEVERITY -->|< 0.3| TIPS[💡 TIPS]
    SEVERITY -->|0.3 - 0.7| SUGGESTION[📋 SUGGESTION]
    SEVERITY -->|> 0.7| ALERT[🚨 ALERT]

    TIPS --> CONFIDENCE{Confidence > 0.5?}
    SUGGESTION --> CONFIDENCE
    ALERT --> CONFIDENCE

    CONFIDENCE -->|Yes| SEND[Send Notification]
    CONFIDENCE -->|No| QUEUE[Queue for Review]
```

---

## Data Models

### Core Events

```python
class SymptomReportedEvent:
    event_id: UUID
    user_id: str
    timestamp: datetime
    symptoms: List[SymptomInput]
    context: Optional[Dict[str, Any]]

class InsightGeneratedEvent:
    event_id: UUID
    source_event_id: UUID
    user_id: str
    insights: List[HealthInsight]
    deficiencies: List[NutritionalDeficiency]
    confidence: float

class AlertTriggeredEvent:
    event_id: UUID
    user_id: str
    alert_level: AlertLevel  # TIPS | SUGGESTION | ALERT
    title: str
    message: str
    recommendations: List[Recommendation]
    products: Optional[List[StandardizedHealthUnit]]
```

### Standardized Health Unit (Vector Storage)

```python
class StandardizedHealthUnit:
    id: str
    source_store: StoreType
    source_product_id: str
    name: str
    description: str
    category: HealthCategory
    subcategory: Optional[str]

    # Nutritional data (normalized)
    nutrients: Dict[str, NutrientValue]
    serving_size: ServingSize

    # Health metadata
    health_claims: List[str]
    allergens: List[str]
    dietary_tags: List[DietaryTag]  # vegan, gluten-free, etc.

    # Vector embedding for semantic search
    embedding: List[float]

    # Pricing/availability
    price: Optional[MoneyAmount]
    availability: AvailabilityStatus
    affiliate_link: Optional[str]
```

---

## Technical Requirements

### Event Processing
- **Message Queue**: Redis Streams or RabbitMQ for event bus
- **Event Schema**: JSON with Pydantic validation
- **Processing Mode**: Async consumers with batch windowing
- **Retry Policy**: Exponential backoff with dead-letter queue

### LLM Integration
- **Primary Provider**: OpenRouter (DeepSeek)
- **Fallback**: OpenAI GPT-4
- **Processing**: Streaming for real-time, batch for historical analysis
- **Caching**: Redis cache for repeated queries

### Vector Database
- **Engine**: Milvus or pgvector
- **Embedding Model**: OpenAI text-embedding-3-small
- **Index Type**: IVF_FLAT for product search
- **Dimensions**: 1536 (OpenAI embeddings)

### Database Schema
- Leverage existing models from `apps/Syntropy-Journals/app/models/syntropy/`
- Extend with new SDO-specific models in `diet/models/`

---

## Implementation Phases

### Phase 1: Core SDO Refactor
- [ ] Merge MPA → SDO architecture
- [ ] Implement event-driven symptom ingestion
- [ ] Create SDO engine with LLM batch/stream processing

### Phase 2: Health Store Agent (HSA)
- [ ] Create AbstractStoreAdapter interface
- [ ] Implement HealthStoreFactory
- [ ] Build ShopStoreAdapter (PoC)
- [ ] Product normalization to StandardizedHealthUnit

### Phase 3: Alert & Notification System
- [ ] Alert classification engine
- [ ] Notification routing (TIPS/SUGGESTION/ALERT)
- [ ] User preference management

### Phase 4: Integration & Testing
- [ ] End-to-end event flow tests
- [ ] LLM batch stream processing tests
- [ ] Data fetch and change capture tests

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Symptom-to-Insight Latency | < 5 seconds |
| Alert Accuracy | > 85% precision |
| Product Match Relevance | > 80% user acceptance |
| System Uptime | 99.9% |

---

## Appendix: Directory Structure

```
diet-insight-engine/
├── diet/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── shared.py
│   │   ├── events.py              # Event schemas
│   │   ├── alerts.py              # Alert/notification models
│   │   └── health_units.py        # StandardizedHealthUnit
│   ├── sdo/                       # Symptom-Diet Optimizer
│   │   ├── __init__.py
│   │   ├── engine.py              # Core SDO engine
│   │   ├── analyzer.py            # LLM symptom analyzer
│   │   ├── correlator.py          # Pattern correlation
│   │   ├── recommender.py         # Diet recommendations
│   │   └── alert_classifier.py    # Alert level classification
│   ├── health_store_agent/        # HSA Ingress
│   │   ├── __init__.py
│   │   ├── factory.py             # HealthStoreFactory
│   │   ├── base_adapter.py        # AbstractStoreAdapter
│   │   ├── normalizer.py          # Product normalizer
│   │   └── adapters/
│   │       ├── __init__.py
│   │       ├── shop_adapter.py    # Shop PoC
│   │       └── amazon_adapter.py  # Amazon integration
│   ├── events/                    # Event bus
│   │   ├── __init__.py
│   │   ├── bus.py                 # Event bus implementation
│   │   ├── consumers.py           # Event consumers
│   │   └── producers.py           # Event producers
│   └── notifications/             # Notification service
│       ├── __init__.py
│       ├── router.py              # Alert routing
│       └── handlers.py            # Notification handlers
└── tests/
    ├── test_sdo_engine.py
    ├── test_health_store_agent.py
    ├── test_events.py
    └── test_notifications.py
```
