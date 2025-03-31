import threading
import string
from contextlib import ExitStack
from decimal import Decimal, getcontext

class ThreadSafeTimeTracker:
    def __init__(self):
        self._sums = {letter: Decimal(0) for letter in string.ascii_lowercase}
        self._counts = {letter: Decimal(0) for letter in string.ascii_lowercase}
        self._locks = {letter: threading.Lock() for letter in string.ascii_lowercase}
        self._lock = threading.Lock()
        # Set the precision for Decimal operations
        getcontext().prec = 30
    
    def record_time(self, letter, amount):
        with self._locks[letter]:
            self._sums[letter] += Decimal(amount)
            self._counts[letter] += Decimal(1)
    
    
    def get_max_letter(self):
        # Acquire all per-letter locks in a consistent order.
        with ExitStack() as stack:
            # Sort the keys to ensure a consistent order (avoid deadlocks)
            for letter in sorted(self._locks):
                stack.enter_context(self._locks[letter])
            # Now that all locks are held, 
            # safely find the character with the max Average time 
            max_avg = Decimal('-inf')
            max_letter = None
            for letter in string.ascii_lowercase:
                avg = Decimal(self._sums[letter]) / Decimal(self._counts[letter]) if self._counts[letter] > 0 else 0
                if avg > max_avg:
                    max_avg = avg
                    max_letter = letter
            return max_letter
            



