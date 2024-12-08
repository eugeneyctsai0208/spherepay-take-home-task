import threading
import time

from contextlib import contextmanager

@contextmanager
def acquire_locks(*locks, retry_delay=0.1, max_retries=None):
    acquired_locks = []
    retries = 0

    # If no max_retries is set, keep trying until locks acquired and operation performed
    while max_retries is None or retries < max_retries:
        try:
            for lock in locks:
                if not lock.acquire(blocking=False):
                    raise RuntimeError("Failed to acquire one of the locks")
                acquired_locks.append(lock)
            yield
            return
        except RuntimeError:
            for lock in reversed(acquired_locks):
                lock.release()
            acquired_locks.clear()

            retries += 1
            time.sleep(retry_delay)
        finally:
            for lock in reversed(acquired_locks):
                lock.release()

    raise RuntimeError(f"Failed to acquire locks after {max_retries} retries")
