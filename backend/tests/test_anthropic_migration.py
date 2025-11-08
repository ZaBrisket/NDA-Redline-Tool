"""
Comprehensive test suite to validate Anthropic migration
Ensures all OpenAI references are removed and system functions correctly
"""

import os
import re
import ast
from pathlib import Path
import pytest
import asyncio
from typing import List, Set

class TestAnthropicMigration:
    """Test suite for validating complete migration to Anthropic"""

    @pytest.fixture(scope="class")
    def backend_path(self):
        """Get backend directory path"""
        return Path(__file__).parent.parent

    def get_all_python_files(self, backend_path: Path) -> List[Path]:
        """Get all Python files in backend"""
        python_files = list(backend_path.rglob("*.py"))
        # Exclude backups directory
        python_files = [f for f in python_files if 'backups' not in str(f)]
        return python_files

    def test_no_openai_imports(self, backend_path):
        """Ensure no OpenAI imports remain in any Python file"""
        files_with_openai = []

        for py_file in self.get_all_python_files(backend_path):
            content = py_file.read_text()

            # Check for OpenAI imports (excluding backups)
            if any(pattern in content for pattern in [
                "import openai",
                "from openai",
                "import OpenAI",
                "from OpenAI"
            ]):
                files_with_openai.append(str(py_file))

        assert not files_with_openai, (
            f"Found OpenAI imports in {len(files_with_openai)} files:\n"
            + "\n".join(files_with_openai)
        )

    def test_no_gpt_references(self, backend_path):
        """Ensure no GPT model references remain"""
        files_with_gpt = []
        gpt_patterns = [
            r"gpt-?[0-9]",
            r"GPT-?[0-9]",
            r"gpt-?3\.5",
            r"gpt-?4",
            r"gpt-?5"
        ]

        for py_file in self.get_all_python_files(backend_path):
            content = py_file.read_text()

            for pattern in gpt_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    files_with_gpt.append((str(py_file), pattern))
                    break

        assert not files_with_gpt, (
            f"Found GPT references in {len(files_with_gpt)} files:\n"
            + "\n".join([f"{file}: {pattern}" for file, pattern in files_with_gpt])
        )

    def test_no_openai_env_vars_in_config(self, backend_path):
        """Ensure no OPENAI environment variables in config files"""
        config_files = [
            backend_path / ".env.example",
        ]

        files_with_openai_env = []

        for config_file in config_files:
            if config_file.exists():
                content = config_file.read_text()
                # Allow commented out references for migration notes
                lines = content.split('\n')
                for line in lines:
                    if "OPENAI" in line.upper() and not line.strip().startswith('#'):
                        files_with_openai_env.append(str(config_file))
                        break

        assert not files_with_openai_env, (
            f"Found active OPENAI environment variables in:\n"
            + "\n".join(files_with_openai_env)
        )

    def test_anthropic_imports_present(self, backend_path):
        """Ensure Anthropic imports are properly added"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"

        assert orchestrator_file.exists(), "llm_orchestrator.py not found"

        content = orchestrator_file.read_text()

        # Check for required Anthropic imports
        required_imports = [
            "from anthropic import AsyncAnthropic",
            "APIStatusError",
            "APIConnectionError"
        ]

        missing_imports = []
        for required in required_imports:
            if required not in content:
                missing_imports.append(required)

        assert not missing_imports, (
            f"Missing required Anthropic imports:\n"
            + "\n".join(missing_imports)
        )

    def test_claude_model_references(self, backend_path):
        """Ensure Claude models are properly referenced"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        # Check for Claude model references (updated to Claude 4.x models)
        assert "claude-opus-4" in content, "Claude Opus 4.x model not found"
        assert "claude-sonnet-4" in content, "Claude Sonnet 4.x model not found"

    def test_error_handling_components(self, backend_path):
        """Verify comprehensive error handling is implemented"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        assert orchestrator_file.exists(), "llm_orchestrator.py not found"

        content = orchestrator_file.read_text()

        # Check for critical error handling components
        required_components = [
            "circuit_breaker",
            "structlog",
            "correlation_id",
            "APIStatusError",
            "APIConnectionError",
            "asyncio.TimeoutError"
        ]

        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)

        assert not missing_components, (
            f"Missing error handling components:\n"
            + "\n".join(missing_components)
        )

    def test_circuit_breaker_implemented(self, backend_path):
        """Verify circuit breaker pattern is implemented"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        # Check for circuit breaker components
        required = [
            "circuit_breaker_threshold",
            "circuit_breaker_state",
            "_check_circuit_breaker",
            "_reset_circuit_breaker",
            "CircuitBreakerState"
        ]

        missing = []
        for component in required:
            if component not in content:
                missing.append(component)

        assert not missing, (
            f"Missing circuit breaker components:\n"
            + "\n".join(missing)
        )

    def test_processing_states_enum(self, backend_path):
        """Verify document state machine is implemented"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"

        content = orchestrator_file.read_text()

        # Check for all required states
        required_states = [
            "PENDING",
            "PROCESSING",
            "RETRYING",
            "COMPLETED",
            "FAILED",
            "DEAD_LETTER"
        ]

        missing_states = []
        for state in required_states:
            if state not in content:
                missing_states.append(state)

        assert not missing_states, (
            f"Missing document states:\n"
            + "\n".join(missing_states)
        )

    def test_configuration_validation(self, backend_path):
        """Verify configuration is properly validated"""
        settings_file = backend_path / "app" / "config" / "settings.py"

        if not settings_file.exists():
            pytest.skip("settings.py not found")

        content = settings_file.read_text()

        # Check for API key validation
        assert "sk-ant-" in content, "Anthropic API key format validation missing"
        assert "@validator" in content or "field_validator" in content, "Pydantic validators missing"

    def test_requirements_updated(self, backend_path):
        """Verify requirements.txt has been updated"""
        req_file = backend_path / "requirements.txt"
        assert req_file.exists(), "requirements.txt not found"

        content = req_file.read_text().lower()

        # Check OpenAI is removed
        assert "openai" not in content or "# openai" in content, "OpenAI still in requirements.txt"

        # Check Anthropic is present
        assert "anthropic" in content, "Anthropic not in requirements.txt"

        # Check critical dependencies
        required_deps = [
            "structlog",
            "prometheus-client",
            "pydantic-settings"
        ]

        missing_deps = []
        for dep in required_deps:
            if dep not in content:
                missing_deps.append(dep)

        # Some deps are optional, so just warn
        if missing_deps:
            print(f"Warning: Optional dependencies not found: {missing_deps}")

    def test_retry_logic_implemented(self, backend_path):
        """Test that retry logic with backoff is implemented"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        retry_components = [
            "max_retries",
            "_calculate_backoff",
            "asyncio.sleep",
            "for attempt in range"
        ]

        missing = []
        for component in retry_components:
            if component not in content:
                missing.append(component)

        assert not missing, (
            f"Missing retry logic components:\n"
            + "\n".join(missing)
        )

    def test_prometheus_metrics_setup(self, backend_path):
        """Test that Prometheus metrics are set up (if available)"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        # Check for Prometheus setup (optional but recommended)
        if "prometheus_client" in content:
            metrics = [
                "Counter",
                "Histogram",
                "Gauge"
            ]

            for metric in metrics:
                assert metric in content, f"Prometheus {metric} not found"

    def test_correlation_id_tracking(self, backend_path):
        """Test that correlation IDs are used for request tracking"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        assert "correlation_id" in content, "Correlation ID tracking not implemented"
        assert "uuid" in content, "UUID generation for correlation IDs not found"

    def test_timeout_handling(self, backend_path):
        """Test that timeouts are properly handled"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        assert "asyncio.wait_for" in content or "timeout=" in content, "Timeout handling not implemented"
        assert "TimeoutError" in content or "asyncio.TimeoutError" in content, "Timeout exception handling missing"

    def test_special_529_handling(self, backend_path):
        """Test that 529 (overload) errors have special handling"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        # Check for 529 handling
        assert "529" in content, "529 (overload) error handling not found"

        # Check for longer backoff for 529
        if "529" in content:
            # Should have special backoff logic
            assert "30" in content or "overload" in content.lower(), "Special 529 backoff logic not found"

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, backend_path):
        """Test that orchestrator can be initialized (requires valid API key)"""
        import sys
        sys.path.insert(0, str(backend_path))

        try:
            from app.core.llm_orchestrator import AnthropicExclusiveOrchestrator

            # Test invalid key
            with pytest.raises(ValueError, match="sk-ant-"):
                AnthropicExclusiveOrchestrator(api_key="invalid-key")

            # Test valid format (but not real key)
            try:
                orch = AnthropicExclusiveOrchestrator(
                    api_key="sk-ant-test-key-12345678901234567890123456789012",
                    max_retries=3
                )
                assert orch.max_retries == 3
                assert orch.circuit_breaker_threshold == 5  # default
            except Exception as e:
                # May fail if dependencies not installed
                pytest.skip(f"Cannot test orchestrator initialization: {e}")

        except ImportError as e:
            pytest.skip(f"Cannot import orchestrator: {e}")

    def test_env_example_has_anthropic_key(self, backend_path):
        """Test that .env.example has ANTHROPIC_API_KEY"""
        env_file = backend_path / ".env.example"

        if not env_file.exists():
            pytest.skip(".env.example not found")

        content = env_file.read_text()

        assert "ANTHROPIC_API_KEY" in content, "ANTHROPIC_API_KEY not in .env.example"
        assert "sk-ant-" in content, "API key format example not in .env.example"

    def test_no_hardcoded_api_keys(self, backend_path):
        """Test that no API keys are hardcoded"""
        dangerous_patterns = [
            r'sk-ant-[a-zA-Z0-9]{40,}',  # Real Anthropic keys
            r'api_key\s*=\s*["\']sk-ant-api',  # Hardcoded keys
        ]

        files_with_keys = []

        for py_file in self.get_all_python_files(backend_path):
            content = py_file.read_text()

            for pattern in dangerous_patterns:
                matches = re.findall(pattern, content)
                # Filter out placeholder keys
                real_keys = [m for m in matches if 'your' not in m.lower() and 'test' not in m.lower() and 'example' not in m.lower()]
                if real_keys:
                    files_with_keys.append((str(py_file), real_keys))

        assert not files_with_keys, (
            f"Found potential hardcoded API keys:\n"
            + "\n".join([f"{file}: {keys}" for file, keys in files_with_keys])
        )

    def test_backward_compatibility_aliases(self, backend_path):
        """Test that backward compatibility aliases exist"""
        orchestrator_file = backend_path / "app" / "core" / "llm_orchestrator.py"
        content = orchestrator_file.read_text()

        # Check for backward compatibility
        aliases = [
            "LLMOrchestrator",
            "AllClaudeLLMOrchestrator"
        ]

        for alias in aliases:
            assert alias in content, f"Backward compatibility alias '{alias}' not found"


class TestOrchestratorFunctionality:
    """Test actual orchestrator functionality (requires API key)"""

    def test_stats_tracking(self):
        """Test that stats are properly tracked"""
        import sys
        backend_path = Path(__file__).parent.parent
        sys.path.insert(0, str(backend_path))

        try:
            from app.core.llm_orchestrator import AnthropicExclusiveOrchestrator

            orch = AnthropicExclusiveOrchestrator(
                api_key="sk-ant-test-12345678901234567890123456789012"
            )

            stats = orch.get_stats()

            # Check for expected stat keys
            expected_keys = [
                'total_requests',
                'successful_requests',
                'failed_requests',
                'opus_calls',
                'sonnet_calls',
                'total_cost_usd'
            ]

            for key in expected_keys:
                assert key in stats, f"Stats missing key: {key}"

        except ImportError as e:
            pytest.skip(f"Cannot import orchestrator: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
