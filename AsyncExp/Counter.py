import string
from decimal import Decimal, getcontext

class Counter:
    def __init__(self):
        self._sums = {letter: Decimal(0) for letter in string.ascii_lowercase}
        self._counts = {letter: Decimal(0) for letter in string.ascii_lowercase}
        # Set the precision for Decimal operations
        getcontext().prec = 30
    
    def record_time(self, letter, amount):
        self._sums[letter] += Decimal(amount)
        self._counts[letter] += Decimal(1)
    
    
    def get_max_letter(self):
        max_avg = Decimal('-inf')
        max_letter = None
        for letter in string.ascii_lowercase:
            avg = Decimal(self._sums[letter]) / Decimal(self._counts[letter]) if self._counts[letter] > 0 else 0
            if avg > max_avg:
                max_avg = avg
                max_letter = letter
        return max_letter
            



