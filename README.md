# ⚡ Timing‑Attack Password Cracker

A proof‑of‑concept Attack showing how **server‑side timing leaks** can reveal a user’s password.  
This hackathon challenge involved of me guessing the password rewuired to log into a web server.
The Server requires a USERNAME & a PASSWORD to log in. additionaly it requires a DIFFICULTY parameter that makes this challenge harder and harder.

---

## Attack Overview

Many back‑ends compare passwords **byte‑by‑byte** and return on the first mismatch:

```python
REAL_PASSWORD = "...."

if not len(input_password) == len(REAL_PASSWORD)
  return False
for i in range(len(input_password)):
    if user_pw[i] != real_pw[i]:
        return False     # <— early exit leaks time
return True
```

The concept is - 
Say we know 4 characters of the password, and we want to find the 5'th.
we can try each possible char and measure the time it takes for the server to respond.
For each wrong char, the server will take approximatly the same time to respond, 
but for the correct char, the server will take a little bit longer to respond...
That is because that for the correct character, the password checking code does not halt and continue to check the 6'th char.
THAT is an amazing vulnerability for to exploit!!

BUT, we have one more PROBLEM, NOISE!
there is a ton of noise in the time measurment, request setup, DNS lookup, delays, losses...
For that I measure a lot of measurements for each possible character, and at the end compare the TRIMMED_MEAN statistic for each character, 
and take the char with the maximum result.


Guy Yehoshua.

