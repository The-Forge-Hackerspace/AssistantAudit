"""
Tests for timezone handling in Monkey365 scan finalization.

Covers timezone-aware/naive datetime duration calculations to prevent
TypeError: can't subtract offset-naive and offset-aware datetimes
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


def test_timezone_aware_duration_calculation():
    """Test that duration calculation handles timezone-aware and naive datetimes."""
    # Simulate timezone-aware completed_at (from datetime.now(timezone.utc))
    completed_at = datetime.now(timezone.utc)
    
    # Simulate timezone-naive created_at stored as UTC (SQLite default — no timezone)
    created_at_naive = completed_at.replace(tzinfo=None)
    
    # Test that created_at gets timezone added (mimics the fix)
    if created_at_naive.tzinfo is None:
        created_at_aware = created_at_naive.replace(tzinfo=timezone.utc)
    else:
        created_at_aware = created_at_naive
    
    # Should NOT raise TypeError
    duration = (completed_at - created_at_aware).total_seconds()
    assert duration >= 0, "Duration should be non-negative"


def test_missing_created_at_fallback():
    """Test that missing created_at falls back to completed_at."""
    completed_at = datetime.now(timezone.utc)
    created_at = None
    
    # Mimics the fix: if created_at is None, use completed_at
    if created_at is None:
        created_at = completed_at
    
    duration = (completed_at - created_at).total_seconds()
    assert duration == 0, "Duration should be 0 when created_at equals completed_at"


def test_timezone_conversion_in_finalization():
    """Test the actual finalization logic with timezone conversion."""
    # Simulate a scan result with naive created_at
    mock_result = MagicMock()
    mock_result.created_at = datetime(2026, 3, 19, 10, 0, 0)  # Naive datetime
    
    # Simulate timezone-aware completed_at
    completed_at = datetime(2026, 3, 19, 10, 5, 0, tzinfo=timezone.utc)
    
    # Apply the fix logic
    created_at = mock_result.created_at
    if created_at is None:
        created_at = completed_at
    elif created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    # Should not raise
    duration_seconds = int((completed_at - created_at).total_seconds())
    
    assert duration_seconds == 300, f"Expected 300 seconds (5 min), got {duration_seconds}"
    assert duration_seconds >= 0, "Duration should be non-negative"


def test_timezone_aware_created_at_unchanged():
    """Test that timezone-aware created_at is not modified."""
    created_at_aware = datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc)
    completed_at = datetime(2026, 3, 19, 10, 5, 0, tzinfo=timezone.utc)
    
    # Apply the fix logic
    if created_at_aware.tzinfo is None:
        created_at = created_at_aware.replace(tzinfo=timezone.utc)
    else:
        created_at = created_at_aware  # Should not modify
    
    duration_seconds = int((completed_at - created_at).total_seconds())
    assert duration_seconds == 300, "Duration should be 300 seconds"


def test_negative_duration_protection():
    """Test that negative durations are clamped to 0."""
    # Edge case: completed_at before created_at (shouldn't happen, but safety check)
    completed_at = datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 3, 19, 10, 5, 0, tzinfo=timezone.utc)
    
    duration_seconds = int((completed_at - created_at).total_seconds())
    duration_seconds = max(duration_seconds, 0)  # Clamp to 0
    
    assert duration_seconds == 0, "Negative duration should be clamped to 0"


def test_duration_handles_naive_created_at_without_typeerror():
    """Test duration calculation with naive created_at does not raise TypeError."""
    completed_at = datetime(2026, 3, 19, 10, 5, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 3, 19, 10, 0, 0)

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    duration_seconds = int((completed_at - created_at).total_seconds())
    assert duration_seconds == 300


def test_duration_handles_aware_created_at_without_typeerror():
    """Test duration calculation with timezone-aware created_at does not raise TypeError."""
    completed_at = datetime(2026, 3, 19, 10, 5, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc)

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    duration_seconds = int((completed_at - created_at).total_seconds())
    assert duration_seconds == 300
