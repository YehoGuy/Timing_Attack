import threading
import string
from contextlib import ExitStack
from decimal import Decimal, getcontext
import statistics

class CharTimer:
    """
    A class to record and analyze timing measurements for each letter.
    It uses a trimmed mean to reduce the impact of outliers.
    The trimmed mean is calculated by discarding the highest
    `trim_percentage` of the measurements, which probably includes all the outliers.
    """
    def __init__(self, trim_percentage=0.05):
        # Store all measurements for each letter.
        self._times = {letter: [] for letter in string.ascii_lowercase}
        self._locks = {letter: threading.Lock() for letter in string.ascii_lowercase}
        getcontext().prec = 30
        self.trim_percentage = trim_percentage  # e.g. 0.2 for top 20%


    def record_time(self, letter, amount):
        """
        Record a timing measurement for a specific letter.
        The amount is converted to Decimal for precision.
        """
        amount = Decimal(amount)
        with self._locks[letter]:
            self._times[letter].append(amount)
    

    def _trimmed_mean(self, measurements):
        """
        Calculate the trimmed mean, discarding the highest trim_percentage.
        """
        if not measurements:
            return Decimal(0)
        # Sort the measurements.
        sorted_times = sorted(measurements)
        n = len(sorted_times)
        # Calculate how many values to trim from the top.
        trim_count = int(self.trim_percentage * n)
        # Keep all values except the highest 'trim_count'
        trimmed = sorted_times[:n - trim_count] if n - trim_count > 0 else sorted_times
        # Use statistics.mean on the trimmed list
        # Convert Decimal to float for statistics.mean, then back to Decimal.
        return Decimal(statistics.mean([float(x) for x in trimmed]))
    

    def get_max_letter(self):
        """
        Get the letter with the maximum trimmed mean time.
        """
        # Acquire all per-letter locks in a consistent order.
        with ExitStack() as stack:
            for letter in sorted(self._locks):
                stack.enter_context(self._locks[letter])
            max_letter = None
            max_trimmed_mean = Decimal('-inf')
            for letter in string.ascii_lowercase:
                tm = self._trimmed_mean(self._times[letter])
                if tm > max_trimmed_mean:
                    max_trimmed_mean = tm
                    max_letter = letter
            return max_letter, max_trimmed_mean
