"""Basic load test (stdlib only).  Usage: python tests/load_test.py http://127.0.0.1:5000 [users] [requests_each]"""
import statistics
import sys
import threading
import time
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
users = int(sys.argv[2]) if len(sys.argv) > 2 else 20
each = int(sys.argv[3]) if len(sys.argv) > 3 else 25
paths = ["/", "/assess", "/health"]
lat, errors, lock = [], [0], threading.Lock()


def worker():
    for i in range(each):
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(base + paths[i % len(paths)], timeout=15) as r:
                r.read()
                ok = r.status == 200
        except Exception:
            ok = False
        dt = (time.perf_counter() - t0) * 1000
        with lock:
            lat.append(dt)
            if not ok:
                errors[0] += 1


start = time.perf_counter()
threads = [threading.Thread(target=worker) for _ in range(users)]
[t.start() for t in threads]
[t.join() for t in threads]
total = time.perf_counter() - start
lat.sort()
print(f"Concurrent users : {users}")
print(f"Total requests   : {len(lat)}")
print(f"Errors           : {errors[0]}")
print(f"Duration         : {total:.2f} s")
print(f"Throughput       : {len(lat)/total:.1f} req/s")
print(f"Latency mean     : {statistics.mean(lat):.1f} ms")
print(f"Latency median   : {statistics.median(lat):.1f} ms")
print(f"Latency p95      : {lat[int(len(lat)*0.95)-1]:.1f} ms")
print(f"Latency max      : {lat[-1]:.1f} ms")
