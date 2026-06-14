import unittest

from task1_sync import run_sync
from task1_threading import run_threading
from task1_multiprocessing import run_multiprocessing
from task1_async import run_asyncio

class TestTask1Calculation(unittest.TestCase):
    """
    Набор unit-тестов для проверки корректности математических вычислений.
    Исключает логические ошибки, возникающие при распределении задач по воркерам.
    """
    def setUp(self):
        self.test_n = 1000
        self.workers = 4
        self.expected_sum = self.test_n * (self.test_n + 1) // 2

    def test_sync_correctness(self):
        result, _ = run_sync(self.test_n)
        self.assertEqual(result, self.expected_sum)

    def test_threading_correctness(self):
        result, _ = run_threading(self.test_n, self.workers)
        self.assertEqual(result, self.expected_sum)

    def test_multiprocessing_correctness(self):
        result, _ = run_multiprocessing(self.test_n, self.workers)
        self.assertEqual(result, self.expected_sum)

    def test_asyncio_correctness(self):
        result, _ = run_asyncio(self.test_n, self.workers)
        self.assertEqual(result, self.expected_sum)

if __name__ == "__main__":
    unittest.main()