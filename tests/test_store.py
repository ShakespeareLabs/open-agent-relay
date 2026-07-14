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
        completed = self.store.complete(task.id, "HELLO")
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        self.assertEqual(completed.result, "HELLO")

    def test_unknown_capability_is_rejected(self) -> None:
        with self.assertRaises(NotFound):
            self.store.submit(Task(capability="missing", input="hello"))

    def test_completed_task_cannot_complete_twice(self) -> None:
        task = self.store.submit(Task(capability="echo", input="hello"))
        self.store.claim("echo")
        self.store.complete(task.id, "done")
        with self.assertRaises(Conflict):
            self.store.complete(task.id, "again")


if __name__ == "__main__":
    unittest.main()

