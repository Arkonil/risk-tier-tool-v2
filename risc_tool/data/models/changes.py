import typing as t
from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from risc_tool.data.models.enums import Signature
from risc_tool.utils.write_once_dict import WriteOnceOrderedDict

ChangeID = tuple[Signature, UUID]
ChangeIDs = set[ChangeID]
CallbackID = UUID
Callback = t.Callable[[ChangeIDs], bool]


class ChangeTracker(ABC):
    @property
    def _signature(self) -> Signature:
        return Signature.CHNAGE_TRACKER

    def __init__(self, dependencies: list["ChangeNotifier"] | None = None):
        self._previous_changes: ChangeIDs = set()
        self._callback_ids: dict[Signature, CallbackID] = {}
        self._dependencies: WriteOnceOrderedDict[Signature, "ChangeNotifier"] = (
            WriteOnceOrderedDict()
        )

        dependencies = dependencies if dependencies else []
        for dependency in dependencies:
            self._dependencies[dependency._signature] = dependency

            callback_id = dependency.subscribe(self._on_dependency_update)
            self._callback_ids[dependency._signature] = callback_id

    def __del__(self):
        for dependency in self._dependencies.values():
            dependency.unsubscribe(self._callback_ids[dependency._signature])

    def _has_changed(self, change_ids: ChangeIDs) -> bool:
        return not self._previous_changes.issuperset(change_ids)

    def _add_changes(self, change_ids: ChangeIDs):
        self._previous_changes.update(change_ids)

    def _on_dependency_update(self, change_ids: ChangeIDs):
        has_changed = self._has_changed(change_ids)

        if has_changed:
            self._add_changes(change_ids)
            self.on_dependency_update(change_ids)

        return has_changed

    @abstractmethod
    def on_dependency_update(self, change_ids: ChangeIDs):
        raise NotImplementedError()


class ChangeNotifier(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.CHANGE_NOTIFIER

    def __init__(self, dependencies: list["ChangeNotifier"] | None = None):
        super().__init__(dependencies)

        self._subscribers: dict[CallbackID, Callback] = {}

    def subscribe(self, callback: Callback) -> CallbackID:
        new_callback_id = uuid4()

        self._subscribers[new_callback_id] = callback

        return new_callback_id

    def unsubscribe(self, callback_id: CallbackID):
        if callback_id in self._subscribers:
            del self._subscribers[callback_id]

    def notify_subscribers(self, change_ids: ChangeIDs):
        for callback in self._subscribers.values():
            callback(change_ids)

    def _on_dependency_update(self, change_ids: ChangeIDs):
        has_changed = super()._on_dependency_update(change_ids)

        if has_changed:
            self.notify_subscribers(change_ids)

        return has_changed
