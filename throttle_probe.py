"""Find a sustainable Goodreads request rate.

Goal is a rate we can hold indefinitely without tripping the bot challenge --
i.e. how to be a polite client, not how to evade one. Writes throttle_log.csv.

Phase 1: fixed interval, distinct URLs, until first HTTP 202 (or cap).
Phase 2: after a trip, probe every 2 min to measure recovery time.
"""
import csv, sys, time, datetime, urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
# Distinct, real, harmless book pages so nothing is served from cache.
IDS = [52783, 2657, 4671, 5107, 7613, 1885, 5470, 320, 968, 30, 5107, 11870085,
       2429135, 6148028, 4667024, 375802, 13496, 18405, 7126, 15881, 34, 890,
       960, 1934, 3636, 5129, 24280, 18619684, 6334, 33574273]


def hit(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=45)
        b = r.read()
        return r.status, len(b)
    except Exception as e:
        return getattr(e, "code", "ERR"), 0


def log(w, fh, **kw):
    kw["t"] = datetime.datetime.now().isoformat(timespec="seconds")
    w.writerow(kw); fh.flush()
    print("   " + "  ".join(f"{k}={v}" for k, v in kw.items()))


def main():
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    fh = open("throttle_log.csv", "w", newline="")
    w = csv.DictWriter(fh, fieldnames=["t", "phase", "n", "interval", "status", "bytes", "ok"])
    w.writeheader()

    print(f"PHASE 1: interval={interval}s")
    tripped_at = None
    for n, bid in enumerate(IDS, 1):
        st, sz = hit(f"https://www.goodreads.com/book/show/{bid}")
        ok = (st == 200 and sz > 5000)
        log(w, fh, phase=1, n=n, interval=interval, status=st, bytes=sz, ok=ok)
        if not ok:
            tripped_at = n
            print(f"   -> tripped after {n} requests at {interval}s spacing "
                  f"({n*interval/60:.1f} min of traffic)")
            break
        time.sleep(interval)

    if tripped_at is None:
        print(f"   -> survived all {len(IDS)} requests at {interval}s; rate looks sustainable")
        fh.close(); return

    print("\nPHASE 2: recovery -- probing every 120s")
    for n in range(1, 11):
        time.sleep(120)
        st, sz = hit("https://www.goodreads.com/book/show/52783")
        ok = (st == 200 and sz > 5000)
        log(w, fh, phase=2, n=n, interval=120, status=st, bytes=sz, ok=ok)
        if ok:
            print(f"   -> recovered after ~{n*2} min")
            break
    fh.close()


if __name__ == "__main__":
    main()
