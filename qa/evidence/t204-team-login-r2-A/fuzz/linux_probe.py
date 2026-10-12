import socket, ipaddress, json, sys
SPELL = ["0.0.0.0", "::", "", "*", "0", "::0", "0:0:0:0:0:0:0:0", "[::]", "0.0.0.00", " 0.0.0.0",
 "0.0.0.0 ", "::ffff:0.0.0.0", "::FFFF:0.0.0.0", "00.0.0.0", "0x0.0.0.0", "0.0.0", "0.0",
 "0000:0000:0000:0000:0000:0000:0000:0000", "::0.0.0.0", " ::", ":: ", "0.0.0.0\t", "0.00.0.0", "::0:0", "0::", "0:0::0",
 "127.1","localhost","LOCALHOST","10.0.0.5 ","[::1]","[2001:db8::5]","intranet.example."]
out={}
for h in SPELL:
    fam = socket.AF_INET6 if h and ":" in h else socket.AF_INET
    s=socket.socket(fam)
    try:
        s.bind((h,0)); b=s.getsockname()[0]; out[h]=f"bound {b} wild={ipaddress.ip_address(b.split('%')[0]).is_unspecified}"
    except Exception as e:
        out[h]=f"{type(e).__name__}: {e}"
    s.close()
for k,v in out.items(): print(repr(k),'->',v)
