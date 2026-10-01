import unittest

from routing.services.throttle import Throttle


class FakeTime:
    def __init__(self):
        self.now = 100.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(round(seconds, 3))
        self.now += seconds


class ThrottleTests(unittest.TestCase):
    def test_first_call_does_not_sleep_second_call_waits(self):
        t = FakeTime()
        th = Throttle(1.1, clock=t.clock, sleep=t.sleep)
        th.wait()
        self.assertEqual(t.slept, [])
        th.wait()                      # immediately after: must wait the full interval
        self.assertEqual(t.slept, [1.1])

    def test_no_sleep_when_enough_time_has_passed(self):
        t = FakeTime()
        th = Throttle(1.1, clock=t.clock, sleep=t.sleep)
        th.wait()
        t.now += 5
        th.wait()
        self.assertEqual(t.slept, [])

    def test_partial_wait(self):
        t = FakeTime()
        th = Throttle(1.1, clock=t.clock, sleep=t.sleep)
        th.wait()
        t.now += 0.4
        th.wait()
        self.assertEqual(t.slept, [0.7])


if __name__ == "__main__":
    unittest.main()
