"""Market benchmark engine for contract clause analysis.

Provides corpus ingestion, PII anonymization, quality filtering,
semantic deduplication, scoring, segmentation, classification,
and freshness tracking for the benchmark corpus.
"""

from __future__ import annotations

from .models import (
    BenchmarkClause,
    BenchmarkCorpusMetadata,
    BenchmarkScore,
    BenchmarkSegment,
    SegmentationResult,
    ContractType,
    IndustryCategory,
    CounterpartyType,
)
from .corpus_ingestion import CorpusIngestionPipeline, IngestionResult
from .anonymizer import PIIAnonymizer, AnonymizationResult
from .quality_filter import QualityFilter, QualityScore
from .deduplicator import SemanticDeduplicator, DeduplicationResult
from .scoring_engine import ScoringEngine, DistributionStats, PercentileScore
from .segmentation import SegmentationEngine, SegmentHierarchy
from .classification import ClauseClassifier, ClassificationResult
from .api import BenchmarkAPI
from .deal_size_extractor import DealSizeExtractor, DealSizeResult
from .industry_classifier import IndustryClassifier
from .counterparty_detector import CounterpartyDetector
from .contract_type_classifier import ContractTypeClassifier
from .override import ClassificationOverride
from .freshness import FreshnessTracker, FreshnessStatus
from .alerting import StalenessAlerter
from .admin_api import AdminAPI

__all__ = [
    "BenchmarkClause",
    "BenchmarkCorpusMetadata",
    "BenchmarkScore",
    "BenchmarkSegment",
    "SegmentationResult",
    "ContractType",
    "IndustryCategory",
    "CounterpartyType",
    "CorpusIngestionPipeline",
    "IngestionResult",
    "PIIAnonymizer",
    "AnonymizationResult",
    "QualityFilter",
    "QualityScore",
    "SemanticDeduplicator",
    "DeduplicationResult",
    "ScoringEngine",
    "DistributionStats",
    "PercentileScore",
    "SegmentationEngine",
    "SegmentHierarchy",
    "ClauseClassifier",
    "ClassificationResult",
    "BenchmarkAPI",
    "DealSizeExtractor",
    "DealSizeResult",
    "IndustryClassifier",
    "CounterpartyDetector",
    "ContractTypeClassifier",
    "ClassificationOverride",
    "FreshnessTracker",
    "FreshnessStatus",
    "StalenessAlerter",
    "AdminAPI",
]
