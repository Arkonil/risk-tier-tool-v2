from unittest.mock import MagicMock
from uuid import UUID

from risc_tool.data.models.changes import ChangeNotifier, ChangeTracker, Signature


class MockNotifier(ChangeNotifier):
    @property
    def _signature(self):
        return Signature.CHANGE_NOTIFIER

    def on_dependency_update(self, change_ids):
        pass


class MockTracker(ChangeTracker):
    @property
    def _signature(self):
        return Signature.CHNAGE_TRACKER

    def on_dependency_update(self, change_ids):
        pass


def test_change_notifier_subscription():
    notifier = MockNotifier()
    callback = MagicMock()

    cb_id = notifier.subscribe(callback)
    assert isinstance(cb_id, UUID)

    notifier.notify_subscribers()
    callback.assert_called_once()

    notifier.unsubscribe(cb_id)
    notifier.notify_subscribers()
    # Should still be 1 call
    assert callback.call_count == 1


def test_change_tracker_dependency_update():
    dependency = MockNotifier()
    tracker = MockTracker(dependencies=[dependency])

    # Mock the abstract method implementation on the instance to track calls
    tracker.on_dependency_update = MagicMock()

    # Trigger notification from dependency
    dependency.notify_subscribers()

    # Tracker should receive update via subscription
    tracker.on_dependency_update.assert_called_once()

    # Check change args
    args, _ = tracker.on_dependency_update.call_args
    change_ids = args[0]
    assert len(change_ids) == 1
    sig, uid = list(change_ids)[0]
    assert sig == Signature.CHANGE_NOTIFIER


def test_change_deduplication():
    dependency = MockNotifier()
    tracker = MockTracker(dependencies=[dependency])
    tracker.on_dependency_update = MagicMock()

    # Generate a fixed set of changes
    data_to_send = {(Signature.DATA_REPOSITORY, 123)}  # Just dummy data types

    # Notifier uses its own wrapping logic in notify_subscribers.
    # But if we go via _on_dependency_update directly?

    # First update
    tracker._on_dependency_update(data_to_send)
    tracker.on_dependency_update.assert_called_once()

    # Second update with SAME changes
    tracker._on_dependency_update(data_to_send)
    # Should NOT call abstract method again because it hasn't changed (superset check)
    assert tracker.on_dependency_update.call_count == 1

    # New change
    new_data = data_to_send | {(Signature.METRIC_REPOSITORY, 456)}
    tracker._on_dependency_update(new_data)
    assert tracker.on_dependency_update.call_count == 2
