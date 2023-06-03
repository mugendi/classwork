"""
 Copyright (c) 2023 Anthony Mugendi
 
 This software is released under the MIT License.
 https://opensource.org/licenses/MIT
"""

import os
import sys
import re
import threading
from hashids import Hashids

def precision_format_time(seconds, precision=2, last_sep = " and "):

    time_dict = {
        "hours": int(seconds // 3600),
        "minutes": int((seconds % 3600) // 60),
        "seconds": int(seconds % 60),
        "milliseconds": int((seconds % 1) * 1000),
        "microseconds": int((seconds % 0.001) * 1000000),
        "nanoseconds": int((seconds % 0.000001) * 1000000000),
        "picoseconds": int((seconds % 0.000000001) * 1000000000000),
        "femtoseconds": int((seconds % 0.000000000001) * 1000000000000000),
        "attoseconds": int((seconds % 0.000000000000001) * 1000000000000000000),
        "zeptoseconds": int((seconds % 0.000000000000000001) * 1000000000000000000000),
        "yoctoseconds": int(
            (seconds % 0.000000000000000000001) * 1000000000000000000000000
        ),
    }

    time_units = {
        "hours": "h",
        "minutes": "m",
        "seconds": "s",
        "milliseconds": "ms",
        "microseconds": "µs",
        "nanoseconds": "ns",
        "picoseconds": "ps",
        "femtoseconds": "fs",
        "attoseconds": "as",
        "zeptoseconds": "zs",
        "yoctoseconds": "ys",
    }
    
    
    time_arr = [f"{val} {time_units[unit]}" for unit, val in time_dict.items() if val>0][0:precision]

    time_str = ""
    
    for i, val in enumerate(time_arr):
        time_str +=  val 
        if i<len(time_arr)-1:
            time_str += ", " if i<len(time_arr)-2 else last_sep 
    
    
    return time_str

def importing_script():
    # get working directory
    dir = os.getcwd()
    # get script path as passed to python
    script = sys.argv[0]
    # if path is not absolute, then join with current dir
    importing_script = (
        os.path.join(dir, script) if not os.path.isabs(script) else script
    )

    return importing_script

def hash_str(text, hash_length="short"):
    import hashlib

    a = hashlib.md5(bytes(text, encoding="utf-8"))
    b = a.hexdigest()
    as_int = int(b, 16)
    if hash_length == "short":
        as_int = int(re.split(r"[\.\+]", str(as_int / 32))[1][:-1])

    hashids = Hashids(salt=text)
    id = hashids.encode(as_int)

    return id

class __c:
    __ne__ = 1

default_props = dir(__c)

def get_class_props(cls):
    props = [
        p for p in dir(cls) if p not in default_props and callable(getattr(cls, p))
    ]

    return props

def sanitize_name(name):
    return re.sub(r"[^\w]", "_", name)

class RaisingThread(threading.Thread):
  def run(self):
    self._exc = None
    try:
      super().run()
    except Exception as e:
      self._exc = e

  def join(self, timeout=None):
    super().join(timeout=timeout)
    
    if self._exc:
      raise self._exc

def trace_caller():
    try:
        raise Exception
    except Exception:
        frame = sys.exc_info()[2].tb_frame.f_back.f_back
        print(" >> invoked by:", frame.f_code.co_name)