"""
Test dependency injection and configuration for Web Research Agent.
Validates settings, HTTP session management, and API client configuration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp
from urllib.robotparser import RobotFileParser

from ..dependencies import WebResearchDependencies
from ..settings import Settings, load_settings


class TestWebResearchDependencies:
    """Test WebResearchDependencies class functionality."""

    def test_dependencies_initialization_minimal(self):
        """Test minimal dependency initialization."""
        deps = WebResearchDependencies(
            brave_api_key="test-brave-key"
        )

        assert deps.brave_api_key == "test-brave-key"
        assert deps.max_results == 20  # Default
        assert deps.quality_threshold == 0.7  # Default
        assert deps.rate_limit_delay == 1.0  # Default
        assert deps.session_id is None  # Default

    def test_dependencies_initialization_complete(self):
        """Test complete dependency initialization."""
        workflow_context = {"workflow_id": "test-123", "stage": "research"}

        deps = WebResearchDependencies(
            brave_api_key="brave-key",
            google_search_api_key="google-key",
            google_search_engine_id="google-cx",
            bing_search_api_key="bing-key",
            max_results=50,
            quality_threshold=0.8,
            request_timeout=60,
            rate_limit_delay=2.0,
            max_parallel_requests=20,
            max_content_length=100000,
            user_agent="CustomAgent/2.0",
            respect_robots_txt=False,
            session_id="session-456",
            workflow_context=workflow_context
        )

        assert deps.brave_api_key == "brave-key"
        assert deps.google_search_api_key == "google-key"
        assert deps.bing_search_api_key == "bing-key"
        assert deps.max_results == 50
        assert deps.quality_threshold == 0.8
        assert deps.session_id == "session-456"
        assert deps.workflow_context == workflow_context

    def test_http_session_lazy_initialization(self):
        """Test HTTP session lazy initialization."""
        deps = WebResearchDependencies(brave_api_key="test")

        # Session should not exist initially
        assert deps._http_session is None

        # First access should create session
        session = deps.http_session
        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)

        # Second access should return same session
        session2 = deps.http_session
        assert session2 is session

    def test_http_session_configuration(self):
        """Test HTTP session configuration."""
        deps = WebResearchDependencies(
            brave_api_key="test",
            request_timeout=45,
            max_parallel_requests=15,
            user_agent="TestAgent/1.0"
        )

        session = deps.http_session

        # Check timeout configuration
        assert session.timeout.total == 45

        # Check connector configuration
        assert session.connector.limit == 15
        assert session.connector.limit_per_host == 5

        # Check headers
        assert session.headers.get("User-Agent") == "TestAgent/1.0"

    def test_available_search_engines_property(self):
        """Test available search engines detection."""
        # Only Brave
        deps_brave = WebResearchDependencies(brave_api_key="brave-key")
        engines = deps_brave.available_search_engines
        assert engines == ["brave"]

        # Brave and Google (requires both API key and engine ID)
        deps_multi = WebResearchDependencies(
            brave_api_key="brave-key",
            google_search_api_key="google-key",
            google_search_engine_id="google-cx"
        )
        engines = deps_multi.available_search_engines
        assert set(engines) == {"brave", "google"}

        # All engines
        deps_all = WebResearchDependencies(
            brave_api_key="brave-key",
            google_search_api_key="google-key",
            google_search_engine_id="google-cx",
            bing_search_api_key="bing-key"
        )
        engines = deps_all.available_search_engines
        assert set(engines) == {"brave", "google", "bing"}

    def test_available_search_engines_no_keys(self):
        """Test error when no API keys are available."""
        deps = WebResearchDependencies()  # No API keys

        with pytest.raises(ValueError, match="No search engine API keys available"):
            _ = deps.available_search_engines

    def test_available_search_engines_caching(self):
        """Test that available engines are cached."""
        deps = WebResearchDependencies(brave_api_key="test")

        # First call
        engines1 = deps.available_search_engines

        # Second call should return cached result
        engines2 = deps.available_search_engines

        assert engines1 is engines2  # Same object reference

    def test_robots_txt_checking_enabled(self):
        """Test robots.txt checking when enabled."""
        deps = WebResearchDependencies(
            brave_api_key="test",
            respect_robots_txt=True
        )

        with patch.object(deps, '_robots_cache', {}) as mock_cache:
            # Mock RobotFileParser
            mock_rp = Mock(spec=RobotFileParser)
            mock_rp.can_fetch.return_value = True

            with patch('agents.web_research_agent.dependencies.RobotFileParser') as mock_rp_class:
                mock_rp_class.return_value = mock_rp

                result = deps.can_scrape_url("https://example.com/page")

                assert result is True
                mock_rp.set_url.assert_called_once()
                mock_rp.read.assert_called_once()
                mock_rp.can_fetch.assert_called_once()

    def test_robots_txt_checking_disabled(self):
        """Test robots.txt checking when disabled."""
        deps = WebResearchDependencies(
            brave_api_key="test",
            respect_robots_txt=False
        )

        # Should always return True when disabled
        result = deps.can_scrape_url("https://example.com/page")
        assert result is True

    def test_robots_txt_error_handling(self):
        """Test robots.txt error handling."""
        deps = WebResearchDependencies(
            brave_api_key="test",
            respect_robots_txt=True
        )

        with patch('agents.web_research_agent.dependencies.RobotFileParser') as mock_rp_class:
            mock_rp = Mock(spec=RobotFileParser)
            mock_rp.read.side_effect = Exception("Network error")
            mock_rp_class.return_value = mock_rp

            # Should return True when robots.txt check fails
            result = deps.can_scrape_url("https://example.com/page")
            assert result is True

    def test_robots_txt_caching(self):
        """Test robots.txt response caching."""
        deps = WebResearchDependencies(
            brave_api_key="test",
            respect_robots_txt=True
        )

        mock_rp = Mock(spec=RobotFileParser)
        mock_rp.can_fetch.return_value = True

        with patch('agents.web_research_agent.dependencies.RobotFileParser') as mock_rp_class:
            mock_rp_class.return_value = mock_rp

            # First call
            result1 = deps.can_scrape_url("https://example.com/page1")

            # Second call to same domain
            result2 = deps.can_scrape_url("https://example.com/page2")

            assert result1 is True
            assert result2 is True

            # RobotFileParser should only be created once (cached)
            assert mock_rp_class.call_count == 1

    @pytest.mark.asyncio
    async def test_cleanup_method(self):
        """Test cleanup method closes HTTP session."""
        deps = WebResearchDependencies(brave_api_key="test")

        # Initialize session
        session = deps.http_session
        assert not session.closed

        # Cleanup
        await deps.cleanup()

        # Session should be closed
        assert session.closed

    @pytest.mark.asyncio
    async def test_cleanup_no_session(self):
        """Test cleanup when no session exists."""
        deps = WebResearchDependencies(brave_api_key="test")

        # Should not raise error when no session exists
        await deps.cleanup()
        assert deps._http_session is None

    def test_from_settings_creation(self):
        """Test creating dependencies from settings."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.brave_api_key = "settings-brave"
        mock_settings.google_search_api_key = "settings-google"
        mock_settings.google_search_engine_id = "settings-cx"
        mock_settings.bing_search_api_key = "settings-bing"
        mock_settings.default_max_results = 25
        mock_settings.default_quality_threshold = 0.75
        mock_settings.request_timeout = 35
        mock_settings.rate_limit_delay = 1.5
        mock_settings.max_parallel_requests = 12
        mock_settings.max_content_length = 60000
        mock_settings.user_agent = "SettingsAgent/1.0"
        mock_settings.respect_robots_txt = False

        deps = WebResearchDependencies.from_settings(mock_settings)

        assert deps.brave_api_key == "settings-brave"
        assert deps.google_search_api_key == "settings-google"
        assert deps.max_results == 25
        assert deps.quality_threshold == 0.75
        assert deps.user_agent == "SettingsAgent/1.0"

    def test_from_settings_with_overrides(self):
        """Test creating dependencies from settings with overrides."""
        mock_settings = Mock()
        mock_settings.brave_api_key = "settings-brave"
        mock_settings.default_max_results = 20
        mock_settings.default_quality_threshold = 0.7
        mock_settings.request_timeout = 30
        mock_settings.rate_limit_delay = 1.0
        mock_settings.max_parallel_requests = 10
        mock_settings.max_content_length = 50000
        mock_settings.user_agent = "SettingsAgent/1.0"
        mock_settings.respect_robots_txt = True

        # Override some values
        deps = WebResearchDependencies.from_settings(
            mock_settings,
            brave_api_key="override-brave",
            max_results=30,
            session_id="override-session",
            custom_field="custom_value"
        )

        assert deps.brave_api_key == "override-brave"  # Overridden
        assert deps.max_results == 30  # Overridden
        assert deps.session_id == "override-session"  # New field
        assert deps.quality_threshold == 0.7  # From settings

        # Custom fields should be passed through
        assert hasattr(deps, 'custom_field')
        assert deps.custom_field == "custom_value"


class TestSettings:
    """Test Settings configuration class."""

    @patch.dict('os.environ', {
        'LLM_API_KEY': 'test-llm-key',
        'BRAVE_API_KEY': 'test-brave-key'
    })
    def test_settings_from_environment(self):
        """Test loading settings from environment variables."""
        settings = Settings()

        assert settings.llm_api_key == "test-llm-key"
        assert settings.brave_api_key == "test-brave-key"

    @patch.dict('os.environ', {
        'LLM_API_KEY': 'test-key',
        'LLM_MODEL': 'gpt-4',
        'DEFAULT_MAX_RESULTS': '30',
        'DEFAULT_QUALITY_THRESHOLD': '0.8'
    })
    def test_settings_type_conversion(self):
        """Test automatic type conversion from environment."""
        settings = Settings()

        assert settings.llm_model == "gpt-4"  # String
        assert settings.default_max_results == 30  # Int
        assert settings.default_quality_threshold == 0.8  # Float

    def test_settings_validation_errors(self):
        """Test settings validation errors."""
        # Empty LLM API key
        with pytest.raises(ValidationError):
            Settings(llm_api_key="")

        # Invalid environment
        with pytest.raises(ValidationError):
            Settings(
                llm_api_key="test",
                app_env="invalid_env"
            )

        # Max results out of range
        with pytest.raises(ValidationError):
            Settings(
                llm_api_key="test",
                default_max_results=200  # > 100
            )

    def test_settings_get_available_search_engines(self):
        """Test getting available search engines from settings."""
        settings = Settings(
            llm_api_key="test",
            brave_api_key="brave-key",
            google_search_api_key="google-key",
            google_search_engine_id="google-cx"
        )

        engines = settings.get_available_search_engines()
        assert set(engines) == {"brave", "google"}

    def test_settings_no_search_engines_error(self):
        """Test error when no search engines are configured."""
        settings = Settings(
            llm_api_key="test"
            # No search engine keys
        )

        with pytest.raises(ValueError, match="At least one search engine API key"):
            settings.get_available_search_engines()

    @patch.dict('os.environ', {
        'LLM_API_KEY': 'test-key',
        'BRAVE_API_KEY': 'brave-key'
    })
    def test_load_settings_success(self):
        """Test successful settings loading."""
        settings = load_settings()

        assert settings.llm_api_key == "test-key"
        assert settings.brave_api_key == "brave-key"

    def test_load_settings_error_handling(self):
        """Test error handling in load_settings."""
        with patch('agents.web_research_agent.settings.Settings') as mock_settings:
            mock_settings.side_effect = Exception("LLM_API_KEY not found")

            with pytest.raises(ValueError, match="Failed to load settings"):
                load_settings()


class TestDependencyIntegration:
    """Test integration between dependencies and other components."""

    def test_dependencies_with_mock_session(self):
        """Test dependencies with mocked HTTP session."""
        deps = WebResearchDependencies(brave_api_key="test")

        # Replace with mock session
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        deps._http_session = mock_session

        # Verify mock is returned
        assert deps.http_session is mock_session

    def test_workflow_context_integration(self):
        """Test workflow context handling."""
        workflow_context = {
            "workflow_id": "research-workflow-789",
            "stage": "information_gathering",
            "priority": "high",
            "deadline": "2024-12-31T23:59:59Z",
            "previous_results": {
                "topic_analysis": "completed",
                "source_identification": "completed"
            }
        }

        deps = WebResearchDependencies(
            brave_api_key="test",
            workflow_context=workflow_context
        )

        assert deps.workflow_context["workflow_id"] == "research-workflow-789"
        assert deps.workflow_context["stage"] == "information_gathering"
        assert deps.workflow_context["priority"] == "high"

    def test_session_tracking(self):
        """Test session tracking functionality."""
        session_id = "user-session-abc123"

        deps = WebResearchDependencies(
            brave_api_key="test",
            session_id=session_id
        )

        assert deps.session_id == session_id

        # Session should be accessible for logging/tracking
        assert deps.session_id is not None

    @pytest.mark.asyncio
    async def test_resource_management(self):
        """Test proper resource management."""
        deps = WebResearchDependencies(brave_api_key="test")

        # Initialize resources
        _ = deps.http_session
        _ = deps.available_search_engines

        # Resources should be properly initialized
        assert deps._http_session is not None
        assert deps._search_engines_available is not None

        # Cleanup should work without errors
        await deps.cleanup()

    def test_configuration_flexibility(self):
        """Test configuration flexibility for different use cases."""
        # High-performance configuration
        high_perf_deps = WebResearchDependencies(
            brave_api_key="test",
            max_parallel_requests=50,
            rate_limit_delay=0.1,
            request_timeout=60,
            max_content_length=200000
        )

        assert high_perf_deps.max_parallel_requests == 50
        assert high_perf_deps.rate_limit_delay == 0.1

        # Conservative configuration
        conservative_deps = WebResearchDependencies(
            brave_api_key="test",
            max_parallel_requests=5,
            rate_limit_delay=2.0,
            request_timeout=10,
            respect_robots_txt=True
        )

        assert conservative_deps.max_parallel_requests == 5
        assert conservative_deps.rate_limit_delay == 2.0
        assert conservative_deps.respect_robots_txt is True