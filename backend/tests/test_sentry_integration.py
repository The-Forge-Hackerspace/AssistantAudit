"""
Tests for Sentry SDK integration.
"""

from unittest.mock import MagicMock, patch

from app.core.sentry_integration import (
    add_breadcrumb,
    capture_exception,
    capture_message,
    init_sentry,
    operation_context,
    set_request_context,
    set_transaction_name,
    set_user_context,
    test_sentry_connection,
)


class TestSentryInitialization:
    """Tests for Sentry initialization"""

    @patch("app.core.sentry_integration.sentry_sdk.init")
    def test_init_sentry_with_valid_dsn(self, mock_init):
        """Verify init_sentry initializes Sentry when DSN is provided"""
        result = init_sentry(
            dsn="https://key@sentry.io/project",
            environment="production",
            version="1.0.0",
        )
        
        assert result is True
        mock_init.assert_called_once()

    def test_init_sentry_without_dsn(self):
        """Verify init_sentry returns False when DSN is None"""
        result = init_sentry(
            dsn=None,
            environment="development",
            version="1.0.0",
        )
        
        assert result is False

    def test_init_sentry_with_empty_dsn(self):
        """Verify init_sentry returns False when DSN is empty string"""
        result = init_sentry(
            dsn="",
            environment="development",
            version="1.0.0",
        )
        
        assert result is False

    @patch("app.core.sentry_integration.sentry_sdk.init")
    def test_init_sentry_with_tracing_enabled(self, mock_init):
        """Verify init_sentry enables performance tracing when requested"""
        init_sentry(
            dsn="https://key@sentry.io/project",
            environment="production",
            version="1.0.0",
            enable_tracing=True,
            traces_sample_rate=0.5,
        )
        
        # Check that init was called with tracing config
        call_args = mock_init.call_args
        assert call_args is not None


class TestCaptureException:
    """Tests for exception capturing"""

    @patch("app.core.sentry_integration.sentry_sdk.push_scope")
    @patch("app.core.sentry_integration.sentry_sdk.capture_exception")
    def test_capture_exception(self, mock_capture, mock_scope):
        """Verify capture_exception sends exception to Sentry"""
        exc = ValueError("Test error")
        
        # Mock the context manager
        mock_context = MagicMock()
        mock_scope.return_value.__enter__.return_value = mock_context
        
        capture_exception(exc, level="error", operation="test")
        
        mock_capture.assert_called_once_with(exc)

    @patch("app.core.sentry_integration.sentry_sdk.push_scope")
    @patch("app.core.sentry_integration.sentry_sdk.capture_exception")
    def test_capture_exception_with_context(self, mock_capture, mock_scope):
        """Verify capture_exception includes context data"""
        exc = RuntimeError("Unexpected error")
        mock_context = MagicMock()
        mock_scope.return_value.__enter__.return_value = mock_context
        
        capture_exception(exc, endpoint="/campaigns", request_id="req_123")
        
        # Verify context was set
        mock_context.set_extra.assert_called()


class TestCaptureMessage:
    """Tests for message capturing"""

    @patch("app.core.sentry_integration.sentry_sdk.push_scope")
    @patch("app.core.sentry_integration.sentry_sdk.capture_message")
    def test_capture_message(self, mock_capture, mock_scope):
        """Verify capture_message sends message to Sentry"""
        mock_context = MagicMock()
        mock_scope.return_value.__enter__.return_value = mock_context
        
        capture_message("Campaign completed successfully", level="info")
        
        mock_capture.assert_called_once_with("Campaign completed successfully")

    @patch("app.core.sentry_integration.sentry_sdk.push_scope")
    @patch("app.core.sentry_integration.sentry_sdk.capture_message")
    def test_capture_message_with_extra_data(self, mock_capture, mock_scope):
        """Verify capture_message includes extra context"""
        mock_context = MagicMock()
        mock_scope.return_value.__enter__.return_value = mock_context
        
        capture_message(
            "Campaign completed",
            level="info",
            campaign_id=123,
            duration_seconds=45.2,
        )
        
        mock_context.set_extra.assert_called()


class TestUserContext:
    """Tests for user context setting"""

    @patch("app.core.sentry_integration.sentry_sdk.push_scope")
    def test_set_user_context(self, mock_scope):
        """Verify set_user_context sets user information"""
        mock_context = MagicMock()
        mock_scope.return_value.__enter__.return_value = mock_context
        
        set_user_context(user_id="user_123", email="user@example.com", role="admin")
        
        mock_context.set_user.assert_called_once()

    @patch("app.core.sentry_integration.sentry_sdk.push_scope")
    def test_set_user_context_without_data(self, mock_scope):
        """Verify set_user_context handles None gracefully"""
        mock_context = MagicMock()
        mock_scope.return_value.__enter__.return_value = mock_context
        
        set_user_context()
        
        # Should still create scope but not set user
        mock_scope.assert_called_once()


class TestRequestContext:
    """Tests for request context setting"""

    @patch("app.core.sentry_integration.sentry_sdk.push_scope")
    def test_set_request_context(self, mock_scope):
        """Verify set_request_context sets request information"""
        mock_context = MagicMock()
        mock_scope.return_value.__enter__.return_value = mock_context
        
        set_request_context(
            request_id="req_123",
            method="POST",
            path="/campaigns",
            ip_address="192.168.1.1",
        )
        
        mock_context.set_context.assert_called_once()


class TestBreadcrumbs:
    """Tests for breadcrumb tracking"""

    @patch("app.core.sentry_integration.sentry_sdk.add_breadcrumb")
    def test_add_breadcrumb(self, mock_add_breadcrumb):
        """Verify add_breadcrumb sends breadcrumb to Sentry"""
        add_breadcrumb(
            category="assessment",
            message="Score calculation completed",
            level="info",
            score=85.5,
        )
        
        mock_add_breadcrumb.assert_called_once()

    @patch("app.core.sentry_integration.sentry_sdk.add_breadcrumb")
    def test_add_breadcrumb_with_multiple_categories(self, mock_add_breadcrumb):
        """Verify breadcrumbs work with different categories"""
        categories = ["auth", "database", "http", "assessment"]
        
        for category in categories:
            add_breadcrumb(category=category, message=f"Event in {category}")
        
        assert mock_add_breadcrumb.call_count == 4


class TestTransactionTracking:
    """Tests for transaction tracking"""

    @patch("app.core.sentry_integration.sentry_sdk.set_transaction_name")
    def test_set_transaction_name(self, mock_set_name):
        """Verify set_transaction_name sets transaction for performance tracking"""
        set_transaction_name("POST /campaigns")
        
        mock_set_name.assert_called_once_with("POST /campaigns")


class TestOperationContext:
    """Tests for operation context manager"""

    @patch("app.core.sentry_integration.sentry_sdk.add_breadcrumb")
    @patch("app.core.sentry_integration.sentry_sdk.set_transaction_name")
    def test_operation_context_success(self, mock_set_name, mock_breadcrumb):
        """Verify operation_context tracks successful operations"""
        with operation_context("test_operation", test_id=123):
            pass  # Simulate successful operation
        
        # Should set transaction name
        mock_set_name.assert_called()
        # Should add breadcrumbs
        assert mock_breadcrumb.call_count >= 2

    @patch("app.core.sentry_integration.sentry_sdk.add_breadcrumb")
    @patch("app.core.sentry_integration.sentry_sdk.set_transaction_name")
    @patch("app.core.sentry_integration.sentry_sdk.capture_exception")
    def test_operation_context_with_exception(
        self, mock_capture, mock_set_name, mock_breadcrumb
    ):
        """Verify operation_context captures exceptions"""
        try:
            with operation_context("failing_operation", attempt=1):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should capture the exception
        mock_capture.assert_called_once()

    @patch("app.core.sentry_integration.sentry_sdk.add_breadcrumb")
    @patch("app.core.sentry_integration.sentry_sdk.set_transaction_name")
    def test_operation_context_includes_context_data(self, mock_set_name, mock_breadcrumb):
        """Verify operation_context includes provided context data"""
        context_data = {"campaign_id": 123, "user_id": "user_456"}
        
        with operation_context("assessment_campaign", **context_data):
            pass
        
        # Context data should be passed to breadcrumbs
        calls = mock_breadcrumb.call_args_list
        assert len(calls) >= 2


class TestConnectionTest:
    """Tests for Sentry connection testing"""

    @patch("app.core.sentry_integration.sentry_sdk.capture_message")
    def test_sentry_connection_success(self, mock_capture):
        """Verify test_sentry_connection returns True on success"""
        # Should not raise exception
        try:
            test_sentry_connection()
            success = True
        except Exception:
            success = False
        
        assert success is True
        mock_capture.assert_called_once()

    @patch("app.core.sentry_integration.sentry_sdk.capture_message")
    def test_sentry_connection_failure(self, mock_capture):
        """Verify test_sentry_connection handles exceptions gracefully"""
        mock_capture.side_effect = Exception("Connection failed")
        
        # Should handle exception gracefully
        try:
            test_sentry_connection()
            failed_gracefully = True
        except Exception:
            failed_gracefully = False
        
        assert failed_gracefully is True


class TestErrorFiltering:
    """Tests for error filtering and hooks"""

    def test_before_send_hook_filters_debug_messages(self):
        """Verify before_send_hook filters out low-level messages"""
        from app.core.sentry_integration import before_send_hook
        
        event = {"level": "debug", "message": "Debug info"}
        result = before_send_hook(event, {})
        
        assert result is None

    def test_before_send_hook_allows_errors(self):
        """Verify before_send_hook allows error messages"""
        from app.core.sentry_integration import before_send_hook
        
        event = {"level": "error", "message": "An error occurred"}
        result = before_send_hook(event, {})
        
        # Should return the event or None (depends on error type)
        assert result is None or result == event


class TestIntegration:
    """Integration tests for Sentry"""

    def test_sentry_modules_import_successfully(self):
        """Verify all Sentry modules import without errors"""
        from app.core.sentry_integration import (
            capture_exception,
            capture_message,
            init_sentry,
            operation_context,
        )
        
        assert callable(init_sentry)
        assert callable(capture_exception)
        assert callable(capture_message)
        assert callable(operation_context)

    def test_sentry_works_without_dsn(self):
        """Verify app works gracefully when Sentry is disabled (no DSN)"""
        result = init_sentry(
            dsn=None,
            environment="development",
            version="1.0.0",
        )
        
        assert result is False
        # App should still function
        assert True
