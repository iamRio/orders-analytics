"""Smoke tests for the initial project scaffold."""

from orders_analytics import main


def test_main_prints_initialization_message(capsys) -> None:
    """The package entry point should expose a stable placeholder message."""
    main()
    captured = capsys.readouterr()
    assert "Orders Analytics is initialized" in captured.out
