"""Comprehensive tests for lintwise.core.logging — structured logging setup."""

from __future__ import annotations

import logging

import structlog

from lintwise.core.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for the setup_logging configuration."""

    def test_sets_root_level(self):
        setup_logging("DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_sets_info_level(self):
        setup_logging("INFO")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_sets_warning_level(self):
        setup_logging("WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_case_insensitive(self):
        setup_logging("debug")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_has_handler(self):
        setup_logging("INFO")
        root = logging.getLogger()
        assert len(root.handlers) >= 1

    def test_no_duplicate_handlers_on_repeat_calls(self):
        setup_logging("INFO")
        setup_logging("INFO")
        setup_logging("INFO")
        root = logging.getLogger()
        # handlers.clear() is called each time, so should only have 1
        assert len(root.handlers) == 1

    def test_silences_noisy_loggers(self):
        setup_logging("DEBUG")
        for name in ("httpx", "httpcore", "openai", "uvicorn.access"):
            logger = logging.getLogger(name)
            assert logger.level >= logging.WARNING

    def test_default_level(self):
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO


class TestGetLogger:
    """Tests for the get_logger helper."""

    def test_returns_bound_logger(self):
        setup_logging("INFO")
        logger = get_logger("test_module")
        assert logger is not None

    def test_logger_can_bind_context(self):
        setup_logging("INFO")
        logger = get_logger("test_module")
        bound = logger.bind(request_id="abc123")
        assert bound is not None

    def test_different_names_different_loggers(self):
        setup_logging("INFO")
        logger1 = get_logger("module_a")
        logger2 = get_logger("module_b")
        # They should be distinct logger instances
        assert logger1 is not logger2

    def test_logger_has_expected_methods(self):
        setup_logging("INFO")
        logger = get_logger("test")
        assert callable(getattr(logger, "info", None))
        assert callable(getattr(logger, "warning", None))
        assert callable(getattr(logger, "error", None))
        assert callable(getattr(logger, "debug", None))
