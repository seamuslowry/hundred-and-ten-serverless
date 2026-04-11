"""Unit tests for PlayerInGame, Human, and NaiveCpu next_action() behaviour."""

import pytest

from src.models.internal.actions import Bid
from src.models.internal.constants import BidAmount
from src.models.internal.player import (
    ConcreteAction,
    Human,
    NaiveCpu,
    NoAction,
    RequestAutomation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bid(player_id: str = "p1", amount: BidAmount = BidAmount.FIFTEEN) -> Bid:
    return Bid(player_id=player_id, amount=amount)


# ---------------------------------------------------------------------------
# Human.next_action() — empty queue
# ---------------------------------------------------------------------------


def test_human_next_action_empty_queue_returns_no_action():
    h = Human(id="p1")
    assert h.next_action() == NoAction()


# ---------------------------------------------------------------------------
# Human.next_action() — single queued action
# ---------------------------------------------------------------------------


def test_human_next_action_single_item_returns_concrete_action():
    h = Human(id="p1")
    action = _bid()
    h.queue_action(action)
    result = h.next_action()
    assert isinstance(result, ConcreteAction)
    assert result.action == action


def test_human_next_action_single_item_removes_it_from_queue():
    h = Human(id="p1")
    h.queue_action(_bid())
    h.next_action()
    assert h.next_action() == NoAction()


# ---------------------------------------------------------------------------
# Human.next_action() — FIFO ordering
# ---------------------------------------------------------------------------


def test_human_next_action_fifo_order():
    """Actions must be returned in insertion order (FIFO), not reversed (LIFO)."""
    h = Human(id="p1")
    a = _bid(amount=BidAmount.FIFTEEN)
    b = _bid(amount=BidAmount.TWENTY)
    h.queue_action(a)
    h.queue_action(b)
    first = h.next_action()
    second = h.next_action()
    assert isinstance(first, ConcreteAction)
    assert isinstance(second, ConcreteAction)
    assert first.action == a
    assert second.action == b


def test_human_next_action_multiple_items_consumed_in_insertion_order():
    """Calling next_action() N times consumes exactly N actions in insertion order."""
    h = Human(id="p1")
    actions = [_bid(amount=BidAmount(v)) for v in (15, 20, 25)]
    for a in actions:
        h.queue_action(a)
    results = [h.next_action() for _ in range(3)]
    assert [r.action for r in results] == actions  # type: ignore[union-attr]
    assert h.next_action() == NoAction()


# ---------------------------------------------------------------------------
# Human queue methods still work on Human instances
# ---------------------------------------------------------------------------


def test_human_queue_action_and_clear_still_work():
    h = Human(id="p1")
    h.queue_action(_bid())
    h.queue_action(_bid(amount=BidAmount.TWENTY))
    h.clear_queued_actions()
    assert h.next_action() == NoAction()


def test_human_queue_action_returns_self():
    h = Human(id="p1")
    result = h.queue_action(_bid())
    assert result is h


def test_human_clear_queued_actions_returns_self():
    h = Human(id="p1")
    result = h.clear_queued_actions()
    assert result is h


# ---------------------------------------------------------------------------
# NaiveCpu.next_action()
# ---------------------------------------------------------------------------


def test_naive_cpu_next_action_returns_request_automation():
    cpu = NaiveCpu(id="cpu1")
    result = cpu.next_action()
    assert isinstance(result, RequestAutomation)


def test_naive_cpu_next_action_always_returns_request_automation():
    """Calling next_action() multiple times always returns RequestAutomation."""
    cpu = NaiveCpu(id="cpu1")
    for _ in range(3):
        assert isinstance(cpu.next_action(), RequestAutomation)


# ---------------------------------------------------------------------------
# ActionRequest types are importable and are the correct kind
# ---------------------------------------------------------------------------


def test_action_request_variants_are_frozen_dataclasses():
    """All three variants must be frozen (immutable)."""
    from dataclasses import FrozenInstanceError

    no_action = NoAction()
    automation = RequestAutomation()
    concrete = ConcreteAction(action=_bid())

    # frozen dataclasses raise FrozenInstanceError on attribute assignment
    with pytest.raises(FrozenInstanceError):
        no_action.nonexistent = 1  # type: ignore[attr-defined]
    with pytest.raises(FrozenInstanceError):
        automation.nonexistent = 1  # type: ignore[attr-defined]
    with pytest.raises(FrozenInstanceError):
        concrete.action = _bid()  # type: ignore[misc]

    # zero-field frozen dataclasses are hashable
    assert hash(no_action) is not None
    assert hash(automation) is not None


def test_no_action_equality():
    assert NoAction() == NoAction()


def test_request_automation_equality():
    assert RequestAutomation() == RequestAutomation()


def test_concrete_action_equality():
    a = _bid()
    assert ConcreteAction(action=a) == ConcreteAction(action=a)
