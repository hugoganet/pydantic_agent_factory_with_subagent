"""Quality Assessment Agent package for source credibility and bias detection."""

from .agent import assess_source_quality, assess_multiple_sources, health_check
from .models import ResearchSource, QualityAssessment
from .settings import settings

__version__ = "1.0.0"
__all__ = [
    "assess_source_quality",
    "assess_multiple_sources",
    "health_check",
    "ResearchSource",
    "QualityAssessment",
    "settings"
]