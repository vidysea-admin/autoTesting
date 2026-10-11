"""Hostile zip builders for the r2.a attack (checker A). Each returns bytes."""
from __future__ import annotations

import io
import random
import struct
import zipfile

from zip_fixtures import video


def _noise(tag, n):
    return random.Random(tag).randbytes(n)


def _zip(members, *, extra=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data, method in members:
            info = zipfile.ZipInfo("p")
            info.filename = name
            info.compress_type = method
            if extra is not None:
                info.extra = extra
            zf.writestr(info, data)
    return buf.getvalue()


def healthy(methods=(0, 8, 14, 12)):
    return _zip([(f"d{i}/m{i}.mp4", _noise(f"m{i}", 3000), m) for i, m in enumerate(methods)]
                + [("notes.txt", b"hello", 0)])


def _find_all(raw, sig):
    out, at = [], raw.find(sig)
    while at != -1:
        out.append(at)
        at = raw.find(sig, at + 4)
    return out


def cd_records(raw):
    return _find_all(raw, b"PK\x01\x02")


def locals_(raw):
    return _find_all(raw, b"PK\x03\x04")


def patch(raw, at, fmt, *vals):
    raw = bytearray(raw)
    struct.pack_into(fmt, raw, at, *vals)
    return bytes(raw)


def flagged(raw, old, new):
    raw = bytearray(raw.replace(old, new))
    for sig, off in ((b"PK\x01\x02", 8), (b"PK\x03\x04", 6)):
        for at in _find_all(bytes(raw), sig):
            raw[at + off + 1] |= 0x08
    return bytes(raw)


def _data_start(raw, n=0):
    d0 = locals_(raw)[n]
    fn = struct.unpack_from("<HH", raw, d0 + 26)
    return d0 + 30 + fn[0] + fn[1]


def cases():
    c = {}
    h = healthy()
    base = _zip([("a.mp4", video("a"), 0), ("b.mp4", video("b"), 0)])
    c["empty_file"] = b""
    c["junk_renamed"] = random.Random(1).randbytes(5000)
    c["pk_only"] = b"PK"
    c["pk0506_only"] = b"PK\x05\x06" + b"\x00" * 18
    c["half_truncated"] = h[: len(h) // 2]
    c["cd_truncated"] = h[: cd_records(h)[0] + 20]
    for label, ex in [("short_zip64_hdr", b"\x01"),
                      ("zip64_len_overrun", b"\x01\x00\x20\x00" + b"\x00" * 3),
                      ("ff_ff_overrun", b"\xff\xff\xff\xff"),
                      ("zip64_empty", b"\x01\x00\x00\x00")]:
        c["extra_" + label] = _zip([("a.mp4", video("a"), 0), ("b.mp4", video("b"), 0)], extra=ex)
    for label, vals in [("2p62", (2**62, 2**62)), ("u64max", (2**64 - 1, 2**64 - 1)),
                        ("zero", (0, 0)), ("usize_big_csize_small", (2**40, 10))]:
        ex = struct.pack("<HHQQ", 1, 16, *vals)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for n in ("a.mp4", "b.mp4"):
                info = zipfile.ZipInfo("p")
                info.filename = n
                info.extra = ex
                zf.writestr(info, video(n))
        raw = buf.getvalue()
        for at in cd_records(raw):
            raw = patch(raw, at + 20, "<II", 0xFFFFFFFF, 0xFFFFFFFF)
        c["zip64_" + label] = raw
    for label, (cs, us) in {"sizes_ffff_noextra": (0xFFFFFFF0, 0xFFFFFFF0),
                            "csize_huge": (0xFFFFFFF0, 4096),
                            "usize_2g_csize_5": (5, 0x7FFFFFFF)}.items():
        raw = base
        for at in cd_records(base):
            raw = patch(raw, at + 20, "<II", cs, us)
        c[label] = raw
    c["offset_absurd"] = patch(base, cd_records(base)[0] + 42, "<I", 0xFFFFFFF0)
    c["offset_into_middle"] = patch(base, cd_records(base)[0] + 42, "<I", 7)
    c["local_fnlen_lie"] = patch(base, locals_(base)[0] + 26, "<HH", 200, 0)
    c["local_extralen_lie"] = patch(base, locals_(base)[0] + 26, "<HH", 5, 60000)
    c["extract_version_ffff"] = patch(base, cd_records(base)[0] + 6, "<H", 0xFFFF)
    c["extract_version_64"] = patch(base, cd_records(base)[0] + 6, "<H", 64)
    for ct in (1, 9, 10, 13, 93, 98, 99, 0xFFFF):
        c[f"ctype_{ct}"] = patch(base, cd_records(base)[0] + 10, "<H", ct)
    c["flag_encrypted_central"] = patch(base, cd_records(base)[0] + 8, "<H", 1)
    c["flag_encrypted_local_only"] = patch(base, locals_(base)[0] + 6, "<H", 1)
    c["flag_strong_enc"] = patch(base, cd_records(base)[0] + 8, "<H", 0x41)
    c["flag_all"] = patch(base, cd_records(base)[0] + 8, "<H", 0xFFFF)
    raw = bytearray(base)
    for sig, off in ((b"PK\x01\x02", 8), (b"PK\x03\x04", 6)):
        for at in _find_all(bytes(raw), sig):
            raw[at + off] |= 1
    c["encrypted_both"] = bytes(raw)
    e = base.rfind(b"PK\x05\x06")
    c["multidisk_eocd"] = patch(base, e + 4, "<HH", 1, 2)
    c["eocd_entries_lie_big"] = patch(base, e + 8, "<HH", 60000, 60000)
    c["eocd_cdsize_lie"] = patch(base, e + 12, "<I", 0xFFFFFFF0)
    c["eocd_cdoffset_lie"] = patch(base, e + 16, "<I", 0xFFFFFFF0)
    c["eocd_comment_overrun"] = patch(base, e + 20, "<H", 0xFFFF)
    c["trailing_junk"] = base + b"x" * 10
    c["zip64_locator_garbage"] = (base[:e] + b"PK\x06\x07" + struct.pack("<IQI", 0, 2**62, 1)
                                  + base[e:])
    lz = _zip([("l.mp4", _noise("lz", 4000), 14), ("ok.mp4", video("ok"), 0)])
    d = _data_start(lz)
    c["lzma_dict_huge"] = patch(lz, d + 5, "<I", 0xFFFFFF00)
    c["lzma_dict_4g"] = patch(lz, d + 5, "<I", 0xFFFFFFFF)
    c["lzma_propssize_huge"] = patch(lz, d + 2, "<H", 0xFFFF)
    c["lzma_propssize_zero"] = patch(lz, d + 2, "<H", 0)
    c["lzma_props_byte_bad"] = patch(lz, d + 4, "<B", 0xFF)
    c["lzma_garbage"] = lz[:d + 9] + random.Random(3).randbytes(len(lz) - d - 9)
    bz = _zip([("b.mp4", _noise("bz", 4000), 12), ("ok.mp4", video("ok"), 0)])
    db = _data_start(bz)
    c["bz2_garbage"] = bz[:db + 4] + random.Random(4).randbytes(100) + bz[db + 104:]
    c["bz2_header_bad"] = patch(bz, db, "<4s", b"XXXX")
    df = _zip([("d.mp4", _noise("df", 4000), 8), ("ok.mp4", video("ok"), 0)])
    dd = _data_start(df)
    c["deflate_garbage"] = df[:dd] + random.Random(5).randbytes(200) + df[dd + 200:]
    two = _zip([("zzz.mp4", video("a"), 0), ("ok.mp4", video("b"), 0)])
    c["name_invalid_utf8_ff"] = flagged(two, b"zzz.mp4", b"\xffzz.mp4")
    c["name_surrogate_cesu"] = flagged(two, b"zzz.mp4", b"\xed\xa0\x80.mp4")
    c["name_overlong"] = flagged(two, b"zzz.mp4", b"\xc0\xafzz.mp")
    c["name_truncated_seq"] = flagged(two, b"zzz.mp4", b"zz\xe2.mp4")
    c["name_nul"] = two.replace(b"zzz.mp4", b"z\x00z.mp4")
    c["name_bidi_rlo"] = flagged(two, b"zzz.mp4", "z‮.mp".encode()[:7].ljust(7, b"p"))
    c["name_cp437_highbytes"] = two.replace(b"zzz.mp4", b"\xff\xfe\xfd.mp4")
    c["unicode_path_extra"] = _zip([("a.mp4", video("a"), 0)],
                                   extra=struct.pack("<HHBI", 0x7075, 5, 1, 0))
    c["nested_zip_by_name"] = _zip([("in.zip", h, 0), ("a.mp4", video("a"), 0)])
    c["zero_byte_member"] = _zip([("e.mp4", b"", 0), ("ok.mp4", video("ok"), 0)])
    c["only_dirs"] = _zip([("d/", b"", 0), ("e/", b"", 0)])
    return c


def fuzz_bases():
    b = [healthy(), healthy((0, 0)), healthy((14, 12, 8))]
    f = []
    for raw in b:
        r = bytearray(raw)
        for sig, off in ((b"PK\x01\x02", 8), (b"PK\x03\x04", 6)):
            for at in _find_all(bytes(r), sig):
                r[at + off + 1] |= 0x08
        f.append(bytes(r))
    return b + f


def mutants(n, seed):
    rng = random.Random(seed)
    bases = fuzz_bases()
    for i in range(n):
        raw = bytearray(bases[i % len(bases)])
        hot = []
        for sig, span in ((b"PK\x01\x02", 66), (b"PK\x03\x04", 50), (b"PK\x05\x06", 22)):
            hot += [(at, span) for at in _find_all(bytes(raw), sig)]
        for _ in range(rng.randint(1, 5)):
            if rng.random() < 0.7 and hot:
                at, span = rng.choice(hot)
                p = min(len(raw) - 1, at + rng.randrange(span))
            else:
                p = rng.randrange(len(raw))
            r = rng.random()
            if r < 0.5:
                raw[p] ^= rng.randint(1, 255)
            elif r < 0.7:
                raw[p] = rng.choice([0, 0xFF, 0x7F, 0x80])
            elif r < 0.85:
                raw[p:p + rng.randint(2, 8)] = rng.randbytes(rng.randint(0, 8))
            else:
                raw[p:p] = rng.randbytes(rng.randint(1, 6))
        if rng.random() < 0.1:
            del raw[rng.randrange(len(raw)):]
        yield i, bytes(raw)
