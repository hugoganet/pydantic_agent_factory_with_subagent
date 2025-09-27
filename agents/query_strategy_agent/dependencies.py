"""
Dependencies for Query Strategy Agent.
Minimal dependencies for pure advisory service.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentDependencies:
    """
    Dependencies for Query Strategy Agent runtime context.

    Minimal dependency set for pure advisory service with workflow integration.
    """

    # Workflow Context (from Research Orchestrator)
    workflow_id: Optional[str] = None
    orchestrator_session_id: Optional[str] = None
    research_context: Optional[Dict[str, Any]] = None

    # Analysis Configuration
    complexity_threshold_low: float = 3.0
    complexity_threshold_high: float = 7.0
    confidence_threshold: float = 0.7

    # Runtime Settings
    max_retries: int = 3
    timeout: int = 30
    debug: bool = False

    # Historical Context (optional for improved recommendations)
    historical_strategies: Optional[List[Dict[str, Any]]] = field(default=None)
    success_metrics: Optional[Dict[str, float]] = field(default=None)

    # NLP Processing Cache (in-memory only)
    _complexity_cache: Dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _strategy_cache: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def cache_complexity_score(self, query: str, score: float):
        """Cache complexity analysis for performance."""
        query_hash = hash(query.lower().strip())
        self._complexity_cache[str(query_hash)] = score

    def get_cached_complexity(self, query: str) -> Optional[float]:
        """Retrieve cached complexity score."""
        query_hash = hash(query.lower().strip())
        return self._complexity_cache.get(str(query_hash))

    def update_historical_context(self, strategy_result: Dict[str, Any]):
        """Update historical context with execution results."""
        if self.historical_strategies is None:
            self.historical_strategies = []

        self.historical_strategies.append(strategy_result)

        # Keep only recent entries to prevent memory bloat
        if len(self.historical_strategies) > 100:
            self.historical_strategies = self.historical_strategies[-50:]

    @classmethod
    def from_settings(cls, settings, **kwargs):
        """
        Create dependencies from settings with overrides.

        Args:
            settings: Settings instance
            **kwargs: Override values

        Returns:
            Configured AgentDependencies instance
        """
        return cls(
            complexity_threshold_low=kwargs.get(
                'complexity_threshold_low',
                settings.complexity_threshold_low
            ),
            complexity_threshold_high=kwargs.get(
                'complexity_threshold_high',
                settings.complexity_threshold_high
            ),
            confidence_threshold=kwargs.get(
                'confidence_threshold',
                settings.default_confidence_threshold
            ),
            max_retries=kwargs.get('max_retries', settings.max_retries),
            timeout=kwargs.get('timeout', settings.timeout_seconds),
            debug=kwargs.get('debug', settings.debug),
            **{k: v for k, v in kwargs.items()
               if k not in [
                   'complexity_threshold_low', 'complexity_threshold_high',
                   'confidence_threshold', 'max_retries', 'timeout', 'debug'
               ]}
        )