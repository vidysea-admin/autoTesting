import asyncio, os, sys, tracemalloc
from pathlib import Path
from starlette.requests import Request
from autotester.ui.upload_stream import stream_upload, UploadRefused

DATA = Path(sys.argv[1])
B = b"XBOUNDARYX"
CT = b"multipart/form-data; boundary=" + B


def req(chunks, ct=CT):
    it = iter(chunks)
    async def receive():
        try:
            c = next(it)
            return {"type": "http.request", "body": c, "more_body": True}
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}
    scope = {"type": "http", "method": "POST", "headers": [(b"content-type", ct)], "path": "/", "query_string": b""}
    return Request(scope, receive)


def part_file(data, name=b"a.mp4", field=b"recording"):
    return (b"--" + B + b'\r\nContent-Disposition: form-data; name="' + field + b'"; filename="' + name +
            b'"\r\nContent-Type: video/mp4\r\n\r\n' + data + b"\r\n")


def part_text(name, val):
    return b"--" + B + b'\r\nContent-Disposition: form-data; name="' + name + b'"\r\n\r\n' + val + b"\r\n"


END = b"--" + B + b"--\r\n"


def split(b, n=65536):
    return [b[i:i + n] for i in range(0, len(b), n)]


async def go(label, chunks, limit, ct=CT):
    d = DATA / label.replace(" ", "_")
    try:
        r = await stream_upload(req(chunks, ct), d, limit)
        print(label.ljust(34), "OK size", r.size, "name", r.filename, "fields", list(r.fields)[:3])
    except UploadRefused as e:
        print(label.ljust(34), "REFUSED", e.status, e.message[:50])
    except BaseException as e:
        print(label.ljust(34), "UNHANDLED", type(e).__name__, str(e)[:60])
    left = list(d.glob("*")) if d.exists() else []
    print("    leftover files in staging:", [(p.name, p.stat().st_size) for p in left])


async def main():
    L = 1000
    await go("exact limit", split(part_file(b"v" * L) + END), L)
    await go("limit plus 1", split(part_file(b"v" * (L + 1)) + END), L)
    await go("no terminal boundary", split(part_file(b"v" * 100)), L)
    await go("cut mid file", split(part_file(b"v" * 100)[:-50]), L)
    await go("no filename", split(part_text(b"recording", b"abc") + END), L)
    await go("two file parts", split(part_file(b"v" * 10) + part_file(b"w" * 10, b"b.mp4") + END), L)
    await go("filename star", split(
        b"--" + B + b'\r\nContent-Disposition: form-data; name="recording"; filename="evil.exe"; filename*=UTF-8\'\'ok.mp4\r\n\r\nabc\r\n' + END), L)
    await go("filename path+nul", split(part_file(b"v" * 10, b"..\\..\\x\x00.mp4") + END), L)
    await go("bare LF body", split(part_file(b"v" * 10).replace(b"\r\n", b"\n") + END.replace(b"\r\n", b"\n")), L)
    await go("huge boundary", split(part_file(b"v" * 10) + END), L, CT + b"A" * 60000)
    # endless body
    def endless():
        yield part_file(b"")[: -2]
        while True:
            yield b"v" * 65536
    await go("endless body", endless(), 5 * 1024 * 1024)

    # memory via text fields: 40 MB of 16 KB fields under a 1 GiB limit
    big = b"".join(part_text(b"f%d" % i, b"z" * 16000) for i in range(2500))  # ~40 MB
    tracemalloc.start()
    await go("2500 x 16K text fields (40MB)", split(big + END), 1 << 30)
    print("    peak traced MB:", tracemalloc.get_traced_memory()[1] / 1e6)
    tracemalloc.stop()
    # many tiny headers in one part
    hdrs = b"".join(b"X-%d: y\r\n" % i for i in range(200000))  # ~2.4 MB of headers
    body = b"--" + B + b'\r\nContent-Disposition: form-data; name="label"\r\n' + hdrs + b"\r\nv\r\n" + END
    tracemalloc.start()
    await go("200k headers in one part", split(body), 1 << 30)
    print("    peak traced MB:", tracemalloc.get_traced_memory()[1] / 1e6)
    tracemalloc.stop()

asyncio.run(main())
