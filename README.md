# DIET (Dietary Intelligence Engine & Tracker)

A comprehensive AI-powered ecosystem for transforming health data into actionable nutritional and meal recommendations. DIET integrates multiple specialized agents:

- **SSS (Symptom Supplemental Solver)**: Core health analysis and nutritional recommendation engine
- **ASA (Amazon Store Agent)**: Product sourcing and purchasing recommendations  
- **MPA (Meal Planner Agent)**: Personalized meal planning and delivery orchestration

### SSS (Symptom Supplemental Solver)
The core intelligence engine located in [`symtom_supplement_dietician/`](./symtom_supplement_dietician/) that handles:
- Health journal parsing and structuring ([`engine.py`](./symtom_supplement_dietician/engine.py))
- Symptom pattern analysis and deficiency identification
- Nutritional and herbal supplement recommendations
- Database storage and retrieval ([`utils/database.py`](./utils/database.py))

### ASA (Amazon Store Agent)
The product sourcing agent in [`amazon_store_agent/`](./amazon_store_agent/) that provides:
- Product search and matching for recommended supplements ([`search.py`](./amazon_store_agent/search.py))
- Pricing and availability information
- Purchase recommendations and affiliate integration ([`affiliate.py`](./amazon_store_agent/affiliate.py))
- Product review and rating analysis

### MPA (Meal Planner Agent)
The meal planning orchestration system in [`meal_planner_agent/`](./diet/meal_planner_agent/) that delivers:
- Personalized meal plan generation based on user preferences and health goals
- CrewAI-powered multi-agent coordination for nutrition optimization
- Integration with meal delivery services (CookUnity-style)
- Cognitive enhancement through strategic nutrition (nootropic optimization)
- Real-time meal plan adaptation and delivery scheduling

The DIET ecosystem combines symptom pattern analysis with nutritional science and real-world product availability to provide complete, actionable health guidance.

## 🎯 DIET System Objective (Core Value Proposition)

The DIET ecosystem establishes a comprehensive 2-part pipeline that transforms health symptoms into actionable product recommendations:

### Phase 0 Architecture
**Part 1: SSS (Symptom Supplemental Solver)**
- Generate symptom-based analysis and evidence-backed diagnosis
- Suggest day-to-day nutritional actions (macronutrients & supplements)
- **Schema Flow**: Health Journal History → Diet-based Diagnosis → Nutritional/Herbal Suggestions (SSS_OUT)

**Part 2: ASA (Amazon Store Agent)**
- Search and recommend Amazon health products based on SSS recommendations
- **Schema Flow**: SSS_OUT → Ranked Affiliated Product Links (ASA_OUT)

### Complete DIET Value Chain
```
Raw Health Journals → [SSS] Analysis & Recommendations → [ASA] Product Sourcing → Actionable Purchase Plan
```

This end-to-end approach ensures users receive not just health insights, but practical, purchasable solutions to address their nutritional needs.

## 🚀 Core Mission & Features

### Primary Mission
Transform unstructured health journal entries into actionable nutritional and supplement recommendations through AI-powered symptom analysis, connecting health insights with real-world product availability.

### Key Capabilities

#### 1. Raw Journal Processing Pipeline (SSS Core)
**Input**: [`RawHealthJournalEntry`](./models/symtom_supplement_dietician/schema.py#L85) (JSON format with unstructured text)
**Output**: [`HealthJournalEntry`](./models/symtom_supplement_dietician/schema.py#L103) (structured, validated health data)

- Parse natural language health journal entries using LLM ([`llm_tools.py`](./tools/llm_tools.py))
- Extract symptoms, diet, lifestyle factors, and wellness scores
- Validate and structure data according to Pydantic schemas ([`schema.py`](./models/symtom_supplement_dietician/schema.py))
- Store processing confidence and metadata

#### 2. Agentic LLM Retrieval & Analysis System (SSS Intelligence)
**Data Source**: PostgreSQL/SQLite database of [`HealthJournalEntry`](./models/symtom_supplement_dietician/schema.py#L103) records
**Analysis Process**: Two-turn AI-powered analysis pipeline ([`engine.py`](./symtom_supplement_dietician/engine.py))

**Turn 1: Symptom Pattern Analysis**
- Query historical health journal entries for user
- Identify symptom patterns, correlations, and trends
- Assess nutritional deficiencies based on symptoms
- Generate [`SymptomAnalysisResult`](./models/symtom_supplement_dietician/schema.py#L167) with confidence scoring

**Turn 2: Nutritional Recommendation Engine**
- Use symptom analysis to generate targeted supplement plans
- Include both traditional nutrients (vitamins/minerals) and herbal supplements
- Provide dosage recommendations and priority scoring
- Generate comprehensive [`NutritionalRecommendationResult`](./models/symtom_supplement_dietician/schema.py#L284)

#### 3. Product Integration & Sourcing (ASA Integration)
- Connect nutritional recommendations to available products
- Source supplements and health products from Amazon marketplace
- Provide pricing, reviews, and availability information
- Enable direct purchasing workflows

#### 4. Configurable Pipeline Features
**Flexible Switches** (configured via YAML):
- `include_herbal_supplements`: Enable/disable herbal supplement recommendations
- `include_amazon_integration`: Connect to Amazon Store Agent for product sourcing
- `analysis_depth`: Control depth of historical data analysis
- `confidence_threshold`: Minimum confidence for recommendations
- `priority_filter`: Focus on high-priority deficiencies only

#### 5. LLM Integration Architecture
- All AI calls use `execute_llm_step()` from [`llm_tools.py`](./tools/llm_tools.py)
- Prompts stored in configuration with `{format_instructions}` placeholders ([`prompts/default.yaml`](./config/prompts/default.yaml))
- Structured Pydantic output parsing with validation
- Configurable model selection via Hydra configuration ([`config_manager.py`](./utils/config_manager.py))

### DIET Ecosystem Components
- **Symptom Analysis**: Advanced pattern recognition in health journal entries
- **Nutritional Deficiency Detection**: Science-based identification of potential deficiencies
- **Personalized Recommendations**: Tailored food and supplement suggestions
- **Product Sourcing**: Real-world availability and purchasing options
- **LangGraph Workflows**: Modular, observable AI pipeline architecture
- **Standalone Modules**: Run symptom analysis or nutrition recommendations independently
- **Comprehensive Logging**: Full traceability and monitoring
- **Scientific Foundation**: Based on established nutritional science principles

## 🏗️ DIET Ecosystem Architecture

The DIET ecosystem consists of integrated AI agents that work together to provide comprehensive health guidance:

### SSS (Symptom Supplemental Solver)
The core intelligence engine located in `symtom_supplement_dietician/` that handles:
- Health journal parsing and structuring
- Symptom pattern analysis and deficiency identification
- Nutritional and herbal supplement recommendations
- Database storage and retrieval

### ASA (Amazon Store Agent)
The product sourcing agent in `amazon_store_agent/` that provides:
- Product search and matching for recommended supplements
- Pricing and availability information
- Purchase recommendations and affiliate integration
- Product review and rating analysis

### DIET Pipeline Integration
The complete workflow connects SSS insights with ASA capabilities:

```
Raw Journal Entry → [SSS] Symptom Analysis → [SSS] Nutrition Recommendations → [ASA] Product Sourcing → Actionable Purchase Plan
       ↓                    ↓                         ↓                           ↓                      ↓
   Database Store → Structured Data → Deficiency ID → Supplement Plan → Available Products → User Action
```

For detailed SSS workflow documentation and design philosophy, see the [SSS Pipeline Documentation](./symtom_supplement_dietician/README.md).

### Success Criteria & Validation

#### Test 1: Raw Journal Parsing (SSS Core)
- Input: Single or multiple [`RawHealthJournalEntry`](./models/symtom_supplement_dietician/schema.py#L85) objects
- Output: Successfully parsed [`HealthJournalEntry`](./models/symtom_supplement_dietician/schema.py#L103) objects with high confidence
- Validation: All Pydantic type constraints satisfied ([`test_engine_basic.py`](./tests/test_engine_basic.py))

#### Test 2: Database Integration & Analysis Pipeline (SSS Intelligence)
- Store parsed health journal entries in SQLite database ([`database.py`](./utils/database.py))
- Execute full 2-turn analysis pipeline with agentic retrieval
- Generate symptom analysis and nutritional recommendations
- Validate output schemas and confidence scores ([`test_diet_pipeline.py`](./tests/test_diet_pipeline.py))

#### Test 3: End-to-End DIET Integration (SSS + ASA)
- Complete pipeline from raw journal to purchasable recommendations
- Validate product matching and availability
- Ensure recommendation confidence and product alignment

### Technical Configuration Management
- Hydra-based configuration loading via [`config_manager.py`](./utils/config_manager.py)
- Pipeline settings in [`config/pipeline/default.yaml`](./config/pipeline/default.yaml)
- LLM configurations in [`config/llm/`](./config/llm/)
- Prompt templates in [`config/prompts/`](./config/prompts/)

### Simplified Workflow Pipeline

The DIET pipeline follows a streamlined process connecting health analysis to actionable product recommendations. View the complete workflow diagram: [workflow_diagram.js](./symtom_supplement_dietician/workflow_diagram.js)

### Core Module Breakdown

### 1. SSS Symptom Analysis Module
- Analyzes structured health journal entries for symptom patterns
- Identifies potential nutritional deficiencies based on symptoms
- Evaluates wellness trends and risk factors
- Calculates confidence scores for analysis reliability

### 2. SSS Nutritional Recommendation Module
- Generates personalized food recommendations based on analysis
- Suggests appropriate supplements for identified deficiencies
- Provides dietary guidelines and foods to avoid
- Creates meal planning tips and lifestyle modifications

### 3. ASA Product Sourcing Module
- Matches recommended supplements to available Amazon products
- Provides product comparison and selection recommendations
- Integrates pricing, shipping, and availability information
- Enables direct purchase workflows with affiliate tracking

### Modular Schema Architecture

The data models have been refactored for clarity and modularity:

- **[`models/shared.py`](./models/shared.py)**: Common enums and base classes used across all modules
- **[`models/symtom_supplement_dietician/schema.py`](./models/symtom_supplement_dietician/schema.py)**: SSS-specific models and workflow schemas
- **[`models/amazon_store_agent/schema.py`](./models/amazon_store_agent/schema.py)**: ASA models for product recommendations
- **[`models/schema.py`](./models/schema.py)**: Legacy import aggregator for backwards compatibility (deprecated)

This modular approach eliminates redundant model definitions and ensures shared components are centralized while keeping module-specific models organized separately.

## 📦 Installation

### Prerequisites
- Python 3.8+
- UV package manager
- OpenAI API key (for LLM functionality)

### Setup

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd diet-insight-engine
```

2. **Install dependencies with UV**:
```bash
uv sync
```

3. **Set up environment variables**:
```bash
cp .env.template .env
# Edit .env with your API keys and configuration
```

4. **Verify installation**:
```bash
python validate_setup.py
```

## ⚙️ Configuration

### Environment Variables

Copy [`.env.template`](./.env.template) to `.env` and configure:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LangSmith Configuration (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=diet-insight-engine

# Application Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
DEBUG=true

# Health Data Processing
MAX_JOURNAL_ENTRIES=1000
SYMPTOM_ANALYSIS_THRESHOLD=0.7
NUTRITION_CONFIDENCE_THRESHOLD=0.6
```

## 🚀 Usage

For detailed usage instructions, run modes, and pipeline configuration, see the [SSS Pipeline Documentation](./symtom_supplement_dietician/README.md).

### Quick Start

**Complete Pipeline with Sample Data**:
```bash
python main.py --user-id user123
```

**Complete Pipeline with Custom Data**:
```bash
python main.py --user-id user123 --input-file journal_entries.json --output-file results.json
```

**SSS Symptom Analysis Only**:
```bash
python main.py --module symptom-analysis --user-id user123 --input-file journal_entries.json
```

**SSS Nutritional Recommendations Only**:
```bash
python main.py --module nutrition-recommendations --user-id user123 --analysis-file symptom_analysis.json
```

**Full DIET Pipeline (SSS + ASA)**:
```bash
python main.py --user-id user123 --include-products --verbose
```

### Command Line Options

```bash
python main.py --help
```

- `--user-id`: User identifier (required)
- `--module`: Module to run (full, symptom-analysis, nutrition-recommendations)
- `--input-file`: JSON file containing health journal entries ([example](./data/synthetic_raw_entries.json))
- `--analysis-file`: JSON file containing symptom analysis results
- `--output-file`: Output file for results
- `--analysis-period-days`: Number of days to analyze (default: 30)
- `--include-supplements`: Include supplement recommendations (default: true)
- `--log-level`: Logging level (default: INFO)

## 📊 Data Models

### Health Journal Entry
See complete schema in [`models/symtom_supplement_dietician/schema.py`](./models/symtom_supplement_dietician/schema.py#L103)
```json
{
  "id": "entry_1",
  "user_id": "user123",
  "timestamp": "2024-01-15T10:30:00",
  "symptoms": [
    {
      "name": "fatigue",
      "severity": "moderate",
      "duration_hours": 8,
      "description": "Persistent tiredness"
    }
  ],
  "overall_wellness": 4,
  "foods_consumed": [
    {
      "name": "oatmeal",
      "meal_type": "breakfast",
      "calories": 300
    }
  ],
  "water_intake_ml": 2000,
  "sleep_hours": 7.5,
  "exercise_minutes": 30,
  "stress_level": 6
}
```

### Pipeline Output
See complete schema in [`models/symtom_supplement_dietician/schema.py`](./models/symtom_supplement_dietician/schema.py#L284)
```json
{
  "pipeline_id": "uuid",
  "user_id": "user123",
  "execution_timestamp": "2024-01-15T15:30:00",
  "symptom_analysis": {
    "identified_deficiencies": [...],
    "symptom_patterns": [...],
    "wellness_trend": "stable",
    "analysis_confidence": 0.85
  },
  "nutritional_recommendations": {
    "food_recommendations": [...],
    "supplement_recommendations": [...],
    "dietary_guidelines": [...],
    "recommendation_confidence": 0.78
  },
  "overall_confidence": 0.82,
  "recommendations_priority": [...]
}
```

## 🧪 Testing

For comprehensive testing documentation, see the [SSS Pipeline Documentation](./symtom_supplement_dietician/README.md#testing).

### Quick Test Commands

**Run all tests**:
```bash
pytest tests/
```

**Run with coverage**:
```bash
pytest tests/ --cov=symtom_supplement_dietician --cov-report=html
```

**Run specific module tests**:
```bash
pytest tests/test_pipeline.py -v
```

**Test individual components**:
- Basic engine: [`tests/test_engine_basic.py`](./tests/test_engine_basic.py)
- Full pipeline: [`tests/test_diet_pipeline.py`](./tests/test_diet_pipeline.py)
- Demo validation: [`symtom_supplement_dietician/demo.py`](./symtom_supplement_dietician/demo.py)

## 📝 Example Use Cases

### 1. Fatigue and Energy Issues
**Input**: Journal entries showing persistent fatigue, poor sleep, processed food consumption
**Output**:
- Identifies potential B12, iron, or magnesium deficiency
- Recommends iron-rich foods, leafy greens, and better sleep hygiene
- Suggests eliminating processed foods and adding whole grains

### 2. Digestive Issues
**Input**: Bloating, irregular digestion, inflammatory symptoms
**Output**:
- Identifies potential food sensitivities or inflammatory patterns
- Recommends anti-inflammatory foods, probiotics
- Suggests elimination diet approach and stress management

### 3. Joint Pain and Inflammation
**Input**: Joint pain, muscle stiffness, inflammatory markers
**Output**:
- Identifies potential omega-3 deficiency or inflammatory diet
- Recommends fatty fish, nuts, turmeric, ginger
- Suggests avoiding processed foods and excessive sugar

## 🔧 Development

### Project Structure
```
diet-insight-engine/
├── config.py                 # Configuration management
├── main.py                   # Main application entry point
├── models/                   # Data models and schemas
│   ├── __init__.py
│   ├── schema.py             # Legacy import aggregator (deprecated)
│   ├── shared.py             # Shared enums and base classes
│   ├── symtom_supplement_dietician/  # SSS-specific models
│   │   └── schema.py
│   └── amazon_store_agent/   # ASA models
│       └── schema.py
├── symtom_supplement_dietician/      # SSS Core pipeline modules
│   ├── __init__.py
│   ├── README.md             # SSS Pipeline documentation
│   ├── workflow_diagram.js   # Mermaid workflow diagram
│   ├── pipeline.py           # Main pipeline orchestration
│   ├── symptom_analyzer.py   # Symptom analysis module
│   └── nutrition_engine.py   # Nutrition recommendations
├── amazon_store_agent/       # ASA Product sourcing modules
│   ├── __init__.py
│   ├── README.md             # ASA documentation
│   ├── search.py             # Product search functionality
│   └── affiliate.py          # Affiliate integration
├── tests/                    # Test suite
├── requirements.txt          # Dependencies
└── .env.template            # Environment variables template
```

### Adding New Features

1. **New Symptom Patterns**: Add to nutritional knowledge in [`config/`](./config/) files
2. **New Nutrients**: Update deficiency patterns in [`engine.py`](./symtom_supplement_dietician/engine.py)
3. **Custom Workflows**: Extend pipeline modules in [`symtom_supplement_dietician/`](./symtom_supplement_dietician/)
4. **New Data Sources**: Add integrations via [`tools/`](./tools/) and [`utils/`](./utils/)

### Code Quality

The project uses:
- **Type Hints**: Full type annotation with Pydantic models ([`schema.py`](./models/symtom_supplement_dietician/schema.py))
- **Logging**: Structured logging throughout the application
- **Error Handling**: Comprehensive error handling and validation
- **Documentation**: Extensive docstrings and comments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [LangGraph](https://langchain-ai.github.io/langgraph/) for AI workflow orchestration
- Nutritional science based on established medical literature
- Uses [OpenAI](https://openai.com/) for natural language processing
- Monitoring with [LangSmith](https://smith.langchain.com/)

## 📞 Support

For questions or issues:
1. Check the [documentation](./docs/)
2. Open an issue on GitHub
3. Contact the development team

---

**Note**: This tool is for informational purposes only and should not replace professional medical advice. Always consult with healthcare providers for medical concerns.
