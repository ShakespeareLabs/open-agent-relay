import time
import unittest

from openagentrelay.models import Capability, Task, TaskStatus
from openagentrelay.store import Conflict, InMemoryStore, NotFound


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryStore()
        self.store.publish(Capability(name="echo"))

    def test_task_lifecycle(self) -> None:
        task = self.store.submit(Task(capability="echo", input="hello"))
        claimed = self.store.claim("echo")
        self.assertEqual(claimed.id, task.id)
        self.assertEqual(claimed.status, TaskStatus.RUNNING)
        completed = self.store.complete(task.id, "HELLO", claimed.lease_id)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        self.assertEqual(completed.result, "HELLO")

    def test_unknown_capability_is_rejected(self) -> None:
        with self.assertRaises(NotFound):
            self.store.submit(Task(capability="missing", input="hello"))

    def test_completed_task_cannot_complete_twice(self) -> None:
        task = self.store.submit(Task(capability="echo", input="hello"))
        claimed = self.store.claim("echo")
        self.store.complete(task.id, "done", claimed.lease_id)
        repeated = self.store.complete(task.id, "done", claimed.lease_id)
        self.assertEqual(repeated.result, "done")
        with self.assertRaises(Conflict):
            self.store.complete(task.id, "again", claimed.lease_id)

    def test_expired_lease_is_requeued(self) -> None:
        store = InMemoryStore(lease_seconds=0.02)
        store.publish(Capability(name="echo"))
        task = store.submit(Task(capability="echo", input="hello"))
        first = store.claim("echo")
        first_lease = first.lease_id
        time.sleep(0.03)
        second = store.claim("echo")
        self.assertEqual(second.id, task.id)
        self.assertNotEqual(second.lease_id, first_lease)
        self.assertEqual(second.attempt, 2)

    def test_retry_stops_at_max_attempts(self) -> None:
        task = self.store.submit(Task(capability="echo", input="hello", max_attempts=2))
        first = self.store.claim("echo")
        retried = self.store.fail(task.id, "temporary", first.lease_id, retryable=True)
        self.assertEqual(retried.status, TaskStatus.PENDING)
        second = self.store.claim("echo")
        failed = self.store.fail(task.id, "still broken", second.lease_id, retryable=True)
        self.assertEqual(failed.status, TaskStatus.FAILED)

    def test_successful_retry_clears_previous_error(self) -> None:
        task = self.store.submit(Task(capability="echo", input="hello", max_attempts=2))
        first = self.store.claim("echo")
        self.store.fail(task.id, "temporary", first.lease_id, retryable=True)
        second = self.store.claim("echo")
        completed = self.store.complete(task.id, "done", second.lease_id)
        self.assertIsNone(completed.error)

    def test_retryable_failure_update_is_idempotent(self) -> None:
        task = self.store.submit(Task(capability="echo", input="hello", max_attempts=2))
        claimed = self.store.claim("echo")
        lease_id = claimed.lease_id
        first = self.store.fail(task.id, "temporary", lease_id, retryable=True)
        repeated = self.store.fail(task.id, "temporary", lease_id, retryable=True)
        self.assertEqual(first.status, TaskStatus.PENDING)
        self.assertEqual(repeated.status, TaskStatus.PENDING)
        self.assertEqual(repeated.attempt, 1)

    def test_stale_lease_cannot_complete_task(self) -> None:
        task = self.store.submit(Task(capability="echo", input="hello"))
        self.store.claim("echo")
        with self.assertRaises(Conflict):
            self.store.complete(task.id, "done", "wrong-lease")


if __name__ == "__main__":
    unittest.main()
