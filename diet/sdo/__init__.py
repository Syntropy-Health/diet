"""
Symptom-Diet Optimizer (SDO)

Core engine that processes symptoms, generates insights, and produces
real-time actionable recommendations for users.

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │              Symptom-Diet Optimizer                 │
    ├─────────────────────────────────────────────────────┤
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
    │  │   Analyzer   │  │  Correlator  │  │Recommender│ │
    │  │  (LLM-based) │  │  (Patterns)  │  │  (Diet)   │ │
    │  └──────┬───────┘  └──────┬───────┘  └─────┬────┘  │
    │         │                 │                │       │
    │         └────────┬────────┴────────────────┘       │
    │                  │                                 │
    │          ┌───────▼───────┐                         │
    │          │Alert Classifier│                        │
    │          └───────┬───────┘                         │
    │                  │                                 │
    └──────────────────┼─────────────────────────────────┘
                       │
                       ▼
              [AlertTriggeredEvent]

Usage:
    from diet.sdo import (
        SDOEngine,
        SymptomAnalyzer,
        PatternCorrelator,
        DietRecommender,
        AlertClassifier,
    )

    engine = SDOEngine()
    await engine.initialize()
    result = await engine.process_symptoms(event)
"""

from .alert_classifier import SDOAlertClassifier
from .analyzer import SymptomAnalyzer
from .correlator import PatternCorrelator
from .engine import SDOEngine, get_sdo_engine
from .recommender import DietRecommender

__all__ = [
    "SDOEngine",
    "get_sdo_engine",
    "SymptomAnalyzer",
    "PatternCorrelator",
    "DietRecommender",
    "SDOAlertClassifier",
]
