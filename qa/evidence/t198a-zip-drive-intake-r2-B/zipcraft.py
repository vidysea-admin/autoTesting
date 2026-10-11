"""Seat B's own zip crafter: builds archives field by field with struct (not the stdlib writer)."""
import bz2
import struct
import zipfile
import zlib

LFH_F = [("sig", "I"), ("vneed", "H"), ("flag", "H"), ("method", "H"), ("time", "H"), ("date", "H"),
         ("crc", "I"), ("csize", "I"), ("usize", "I"), ("nlen", "H"), ("elen", "H")]
CDH_F = [("sig", "I"), ("vmade", "H"), ("vneed", "H"), ("flag", "H"), ("method", "H"), ("time", "H"),
         ("date", "H"), ("crc", "I"), ("csize", "I"), ("usize", "I"), ("nlen", "H"), ("elen", "H"),
         ("clen", "H"), ("disk", "H"), ("iattr", "H"), ("eattr", "I"), ("offset", "I")]
EOCD_F = [("sig", "I"), ("disk", "H"), ("cddisk", "H"), ("nd", "H"), ("n", "H"), ("cdsize", "I"),
          ("cdoff", "I"), ("clen", "H")]
MAXV = {"H": 0xFFFF, "I": 0xFFFFFFFF}


def pk(fields, vals):
    return b"".join(struct.pack("<" + f, vals[n] & MAXV[f]) for n, f in fields)


def raw_deflate(b):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(b) + c.flush()


def entry(name, data, method=0, **kw):
    """One entry: comp data computed here; lfh/cdh overrides via kw lfh={}, cdh={}, lextra, cextra."""
    if isinstance(name, str):
        name = name.encode("utf-8")
    if method == 0:
        comp = data
    elif method == 8:
        comp = raw_deflate(data)
    elif method == 12:
        comp = bz2.compress(data)
    else:
        comp = kw.pop("comp", data)
    crc = zlib.crc32(data)
    e = dict(name=name, comp=comp, method=method, crc=crc, usize=len(data), csize=len(comp),
             flag=0, vneed=20, vmade=20, lextra=b"", cextra=b"", comment=b"", eattr=0, iattr=0,
             disk=0, lfh={}, cdh={}, offset=None)
    e.update(kw)
    return e


def build(entries, eocd=None, comment=b"", prefix=b"", tail=b"", skip_cd=False, cd_name=None):
    out = bytearray(prefix)
    offs = []
    for e in entries:
        offs.append(len(out))
        v = dict(sig=0x04034B50, vneed=e["vneed"], flag=e["flag"], method=e["method"], time=0,
                 date=0x21, crc=e["crc"], csize=e["csize"], usize=e["usize"],
                 nlen=len(e["name"]), elen=len(e["lextra"]))
        v.update(e["lfh"])
        out += pk(LFH_F, v) + e["name"] + e["lextra"] + e["comp"]
    cdstart = len(out)
    cd = bytearray()
    for e, off in zip(entries, offs):
        cname = e["name"] if cd_name is None else cd_name
        v = dict(sig=0x02014B50, vmade=e["vmade"], vneed=e["vneed"], flag=e["flag"],
                 method=e["method"], time=0, date=0x21, crc=e["crc"], csize=e["csize"],
                 usize=e["usize"], nlen=len(cname), elen=len(e["cextra"]),
                 clen=len(e["comment"]), disk=e["disk"], iattr=e["iattr"], eattr=e["eattr"],
                 offset=off if e["offset"] is None else e["offset"])
        v.update(e["cdh"])
        cd += pk(CDH_F, v) + cname + e["cextra"] + e["comment"]
    if not skip_cd:
        out += cd
    ev = dict(sig=0x06054B50, disk=0, cddisk=0, nd=len(entries), n=len(entries), cdsize=len(cd),
              cdoff=cdstart, clen=len(comment))
    ev.update(eocd or {})
    out += pk(EOCD_F, ev) + comment + tail
    return bytes(out)


def video(tag, size=4096):
    return (f"MP4-{tag}|".encode() * (size // 8 + 1))[:size]


def healthy_entries():
    """stored, deflate, bzip2 and lzma members (lzma comes from the stdlib writer's own bytes)."""
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_LZMA) as z:
        z.writestr("l.mp4", video("l", 3000))
    raw = buf.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        i = z.getinfo("l.mp4")
        start = i.header_offset + 30 + len("l.mp4")
        lz = raw[start:start + i.compress_size]
    return [entry("a.mp4", video("a")), entry("b.mp4", video("b", 5000), 8),
            entry("c.mp4", video("c", 3000), 12),
            entry("l.mp4", video("l", 3000), 14, comp=lz)]
