"""Unit tests for MiniMax provider integration in Code2Video."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestMiniMaxConfig(unittest.TestCase):
    """Tests for MiniMax configuration in api_config.json."""

    def setUp(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "src", "api_config.json")
        with open(config_path, "r") as f:
            self.config = json.load(f)

    def test_minimax_entry_exists(self):
        """MiniMax should be present in api_config.json."""
        self.assertIn("minimax", self.config)

    def test_minimax_base_url(self):
        """MiniMax base_url should point to the official API endpoint."""
        self.assertEqual(self.config["minimax"]["base_url"], "https://api.minimax.io/v1")

    def test_minimax_model(self):
        """MiniMax model should default to MiniMax-M2.7."""
        self.assertEqual(self.config["minimax"]["model"], "MiniMax-M2.7")

    def test_minimax_has_api_key_placeholder(self):
        """MiniMax should have an api_key placeholder."""
        self.assertIn("api_key", self.config["minimax"])

    def test_minimax_config_keys(self):
        """MiniMax config should have base_url, api_key, and model."""
        expected_keys = {"base_url", "api_key", "model"}
        self.assertEqual(set(self.config["minimax"].keys()), expected_keys)


class TestMiniMaxRequestFunctions(unittest.TestCase):
    """Tests for request_minimax and request_minimax_token functions."""

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_returns_content(self, mock_openai_cls, mock_cfg):
        """request_minimax should return stripped content from the response."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  Hello from MiniMax  "
        mock_client.chat.completions.create.return_value = mock_response

        from gpt_request import request_minimax

        result = request_minimax("test prompt")
        self.assertEqual(result, "Hello from MiniMax")

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_uses_correct_model(self, mock_openai_cls, mock_cfg):
        """request_minimax should pass the correct model name."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_client.chat.completions.create.return_value = mock_response

        from gpt_request import request_minimax

        request_minimax("test prompt")
        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs["model"], "MiniMax-M2.7")

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_uses_openai_client(self, mock_openai_cls, mock_cfg):
        """request_minimax should use OpenAI client (not AzureOpenAI)."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_client.chat.completions.create.return_value = mock_response

        from gpt_request import request_minimax

        request_minimax("test prompt")
        mock_openai_cls.assert_called_with(base_url="https://api.minimax.io/v1", api_key="test-key")

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_token_returns_tuple(self, mock_openai_cls, mock_cfg):
        """request_minimax_token should return (completion, usage_info) tuple."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_client.chat.completions.create.return_value = mock_response

        from gpt_request import request_minimax_token

        completion, usage_info = request_minimax_token("test prompt")
        self.assertIs(completion, mock_response)
        self.assertEqual(usage_info["prompt_tokens"], 10)
        self.assertEqual(usage_info["completion_tokens"], 20)
        self.assertEqual(usage_info["total_tokens"], 30)

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_token_no_usage(self, mock_openai_cls, mock_cfg):
        """request_minimax_token should handle missing usage gracefully."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        from gpt_request import request_minimax_token

        completion, usage_info = request_minimax_token("test prompt")
        self.assertEqual(usage_info["prompt_tokens"], 0)
        self.assertEqual(usage_info["completion_tokens"], 0)
        self.assertEqual(usage_info["total_tokens"], 0)

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_retry_on_failure(self, mock_openai_cls, mock_cfg):
        """request_minimax should retry on failure up to max_retries."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "success"
        mock_client.chat.completions.create.side_effect = [
            Exception("temporary error"),
            mock_response,
        ]

        from gpt_request import request_minimax

        result = request_minimax("test prompt", max_retries=3)
        self.assertEqual(result, "success")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_max_retries_exceeded(self, mock_openai_cls, mock_cfg):
        """request_minimax should raise after max_retries failures."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("persistent error")

        from gpt_request import request_minimax

        with self.assertRaises(Exception) as ctx:
            request_minimax("test prompt", max_retries=2)
        self.assertIn("Failed after 2 attempts", str(ctx.exception))

    @patch("gpt_request.cfg")
    @patch("gpt_request.OpenAI")
    def test_request_minimax_max_tokens_param(self, mock_openai_cls, mock_cfg):
        """request_minimax should pass max_tokens to the API."""
        mock_cfg.side_effect = lambda svc, key, default=None: {
            ("minimax", "base_url"): "https://api.minimax.io/v1",
            ("minimax", "api_key"): "test-key",
            ("minimax", "model"): "MiniMax-M2.7",
        }.get((svc, key), default)

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_client.chat.completions.create.return_value = mock_response

        from gpt_request import request_minimax

        request_minimax("test prompt", max_tokens=16384)
        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs["max_tokens"], 16384)


class TestMiniMaxAgentIntegration(unittest.TestCase):
    """Tests for MiniMax integration in the agent module."""

    def _setup_agent_mocks(self):
        """Set up mocks for agent module import with proper star-import support."""
        import types

        # Create a proper module (not MagicMock) so 'from gpt_request import *' works
        mock_gpt_request = types.ModuleType("gpt_request")
        # Define all the function names that agent.py uses via `from gpt_request import *`
        func_names = [
            "request_gpt41_token", "request_claude_token", "request_gpt5_token",
            "request_gpt4o_token", "request_o4mini_token", "request_gemini_token",
            "request_minimax_token", "request_gpt41", "request_claude",
            "request_gpt5", "request_gpt4o", "request_o4mini", "request_gemini",
            "request_minimax", "request_gemini_video_img",
        ]
        for name in func_names:
            setattr(mock_gpt_request, name, MagicMock(name=name))
        mock_gpt_request.__all__ = func_names

        sys.modules["gpt_request"] = mock_gpt_request
        # Mock other imports that agent.py needs
        for mod_name in ["prompts", "utils", "scope_refine", "manim"]:
            mock_mod = types.ModuleType(mod_name)
            # agent.py uses `from utils import *` etc., provide empty __all__
            mock_mod.__all__ = []
            sys.modules[mod_name] = mock_mod

        # external_assets needs process_storyboard_with_assets as named import
        mock_external = types.ModuleType("external_assets")
        mock_external.__all__ = []
        mock_external.process_storyboard_with_assets = MagicMock(name="process_storyboard_with_assets")
        sys.modules["external_assets"] = mock_external

        return mock_gpt_request

    def _cleanup_agent_mocks(self):
        """Remove mocked modules."""
        for mod in ["agent", "gpt_request", "prompts", "utils", "scope_refine", "external_assets", "manim"]:
            sys.modules.pop(mod, None)

    def test_agent_mapping_includes_minimax(self):
        """get_api_and_output should include 'minimax' in its mapping."""
        mock_gpt_request = self._setup_agent_mocks()
        try:
            if "agent" in sys.modules:
                del sys.modules["agent"]
            import agent

            api_func, folder_name = agent.get_api_and_output("minimax")
            self.assertEqual(folder_name, "MiniMax")
        finally:
            self._cleanup_agent_mocks()

    def test_agent_argparse_accepts_minimax(self):
        """build_and_parse_args should accept 'minimax' as a valid --API choice."""
        self._setup_agent_mocks()
        try:
            if "agent" in sys.modules:
                del sys.modules["agent"]
            import agent

            original_argv = sys.argv
            sys.argv = ["agent.py", "--API", "minimax"]
            try:
                args = agent.build_and_parse_args()
                self.assertEqual(args.API, "minimax")
            finally:
                sys.argv = original_argv
        finally:
            self._cleanup_agent_mocks()

    def test_agent_invalid_api_raises(self):
        """get_api_and_output should raise ValueError for unknown API name."""
        self._setup_agent_mocks()
        try:
            if "agent" in sys.modules:
                del sys.modules["agent"]
            import agent

            with self.assertRaises(ValueError):
                agent.get_api_and_output("nonexistent-provider")
        finally:
            self._cleanup_agent_mocks()


class TestMiniMaxIntegration(unittest.TestCase):
    """Integration tests for MiniMax API (require MINIMAX_API_KEY)."""

    def setUp(self):
        self.api_key = os.environ.get("MINIMAX_API_KEY")
        if not self.api_key:
            self.skipTest("MINIMAX_API_KEY not set")

    @patch("gpt_request._CFG", {
        "minimax": {
            "base_url": "https://api.minimax.io/v1",
            "api_key": "",
            "model": "MiniMax-M2.7",
        }
    })
    def test_live_minimax_request(self):
        """Integration: request_minimax should return a non-empty string."""
        os.environ["MINIMAX_API_KEY"] = self.api_key
        try:
            from gpt_request import request_minimax
            result = request_minimax("Say hello in one word.", max_tokens=50, max_retries=2)
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
        finally:
            pass

    @patch("gpt_request._CFG", {
        "minimax": {
            "base_url": "https://api.minimax.io/v1",
            "api_key": "",
            "model": "MiniMax-M2.7",
        }
    })
    def test_live_minimax_token_tracking(self):
        """Integration: request_minimax_token should return valid token counts."""
        os.environ["MINIMAX_API_KEY"] = self.api_key
        try:
            from gpt_request import request_minimax_token
            completion, usage = request_minimax_token("Say hello.", max_tokens=50, max_retries=2)
            self.assertIsNotNone(completion)
            self.assertGreater(usage["total_tokens"], 0)
        finally:
            pass

    @patch("gpt_request._CFG", {
        "minimax": {
            "base_url": "https://api.minimax.io/v1",
            "api_key": "",
            "model": "MiniMax-M2.7",
        }
    })
    def test_live_minimax_long_response(self):
        """Integration: request_minimax should handle longer responses."""
        os.environ["MINIMAX_API_KEY"] = self.api_key
        try:
            from gpt_request import request_minimax
            result = request_minimax(
                "Briefly explain the Fourier Transform in 2-3 sentences.",
                max_tokens=200,
                max_retries=2,
            )
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 20)
        finally:
            pass


if __name__ == "__main__":
    unittest.main()
