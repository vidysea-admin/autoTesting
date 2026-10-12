import sys
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]
src = open(sys.argv[0].replace("f2_headers.py", "f2_measure.py")).read().split("only = sys.argv")[0]
exec(compile(src, "f2_measure_head", "exec"))
def hdr_flood(n, distinct=True):
    def g():
        yield f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="f"\r\n'.encode()
        batch = []
        for i in range(n):
            batch.append(f"X-{i if distinct else 0}: v\r\n")
            if len(batch) >= 5000: yield "".join(batch).encode(); batch = []
        if batch: yield "".join(batch).encode()
        yield b"\r\nval\r\n"
        yield filepart_head(); yield from filechunks(4096); yield multipart_tail()
    return g
for n in (10_000, 100_000, 400_000):
    run(f"E {n} distinct headers in one part", hdr_flood(n), limit=64 * MIB)
run("E 400000 identical-name headers in one part", hdr_flood(400_000, False), limit=64 * MIB)
