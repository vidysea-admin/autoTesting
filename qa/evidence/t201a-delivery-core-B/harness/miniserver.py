"""Loopback SMTP server for the blind wire check (checker B). Binds 127.0.0.1 only."""
import base64, socket, ssl, threading, time, datetime, ipaddress, os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_certs(d):
    os.makedirs(d, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC)

    def name(cn):
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    ca_key = _key()
    ca = (x509.CertificateBuilder().subject_name(name("wire-ca")).issuer_name(name("wire-ca"))
          .public_key(ca_key.public_key()).serial_number(1)
          .not_valid_before(now - datetime.timedelta(days=1))
          .not_valid_after(now + datetime.timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                                       content_commitment=False, key_encipherment=False,
                                       data_encipherment=False, key_agreement=False,
                                       encipher_only=False, decipher_only=False), critical=True)
          .sign(ca_key, hashes.SHA256()))

    def leaf(cn, sans, serial):
        k = _key()
        c = (x509.CertificateBuilder().subject_name(name(cn)).issuer_name(ca.subject)
             .public_key(k.public_key()).serial_number(serial)
             .not_valid_before(now - datetime.timedelta(days=1))
             .not_valid_after(now + datetime.timedelta(days=2))
             .add_extension(x509.SubjectAlternativeName(sans), critical=False)
             .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
             .sign(ca_key, hashes.SHA256()))
        return k, c

    def write(prefix, k, c):
        open(f"{d}/{prefix}.key", "wb").write(k.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))
        open(f"{d}/{prefix}.crt", "wb").write(c.public_bytes(serialization.Encoding.PEM))

    open(f"{d}/ca.pem", "wb").write(ca.public_bytes(serialization.Encoding.PEM))
    write("good", *leaf("127.0.0.1", [x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                                      x509.DNSName("localhost")], 2))
    write("wrong", *leaf("other.invalid", [x509.DNSName("other.invalid")], 3))
    sk = _key()
    ss = (x509.CertificateBuilder().subject_name(name("127.0.0.1")).issuer_name(name("127.0.0.1"))
          .public_key(sk.public_key()).serial_number(4)
          .not_valid_before(now - datetime.timedelta(days=1))
          .not_valid_after(now + datetime.timedelta(days=2))
          .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                         critical=False)
          .sign(sk, hashes.SHA256()))
    write("selfsigned", sk, ss)
    return d


class Conn:
    def __init__(self, s):
        self.s, self.buf = s, b""

    def line(self):
        while b"\r\n" not in self.buf:
            d = self.s.recv(4096)
            if not d:
                raise EOFError
            self.buf += d
        l, self.buf = self.buf.split(b"\r\n", 1)
        return l

    def until(self, term):
        while term not in self.buf:
            d = self.s.recv(4096)
            if not d:
                raise EOFError
            self.buf += d
        i = self.buf.index(term) + len(term)
        out, self.buf = self.buf[:i], self.buf[i:]
        return out

    def send(self, t):
        self.s.sendall(t.encode() + b"\r\n")


class Server:
    """kwargs: tls (none|starttls|implicit), advertise_starttls, cert (good|wrong|selfsigned), certdir,
    auth (accept|reject|none), rcpt (accept|reject), data (accept|drop_mid|drop_after_full|error),
    silent (None|no_banner|after_ehlo|after_mailfrom|dribble)"""

    def __init__(self, **kw):
        self.kw = dict(tls="none", advertise_starttls=True, cert="good", auth="accept", rcpt="accept",
                       data="accept", silent=None)
        self.kw.update(kw)
        self.events = []
        self.messages = []
        self.auth_attempts = []
        self.errors = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self._stop = False
        self.conns = []
        threading.Thread(target=self._loop, daemon=True).start()

    def close(self):
        self._stop = True
        try:
            self.sock.close()
        except OSError:
            pass
        for c in self.conns:
            try:
                c.close()
            except OSError:
                pass

    def _ctx(self):
        c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        d = self.kw["certdir"]
        n = self.kw["cert"]
        c.load_cert_chain(f"{d}/{n}.crt", f"{d}/{n}.key")
        return c

    def _loop(self):
        while not self._stop:
            try:
                s, _ = self.sock.accept()
            except OSError:
                return
            self.conns.append(s)
            threading.Thread(target=self._serve, args=(s,), daemon=True).start()

    def _serve(self, s):
        kw = self.kw
        try:
            s.settimeout(30)
            if kw["tls"] == "implicit":
                try:
                    s = self._ctx().wrap_socket(s, server_side=True)
                except (ssl.SSLError, OSError) as e:
                    self.events.append(("tls-handshake-failed", type(e).__name__))
                    return
            c = Conn(s)
            if kw["silent"] == "no_banner":
                time.sleep(60)
                return
            c.send("220 wire.example.test ESMTP ready")
            if kw["silent"] == "dribble":
                for _ in range(40):
                    s.sendall(b"2")
                    time.sleep(0.5)
                return
            tls_done = kw["tls"] == "implicit"
            while True:
                l = c.line().decode("utf-8", "replace")
                u = l.upper()
                self.events.append(("cmd", l if not u.startswith("AUTH") else "AUTH <not-logged>"))
                if u.startswith("EHLO") or u.startswith("HELO"):
                    if kw["silent"] == "after_ehlo":
                        time.sleep(60)
                        return
                    lines = ["250-wire.example.test"]
                    if kw["advertise_starttls"] and kw["tls"] == "starttls" and not tls_done:
                        lines.append("250-STARTTLS")
                    if kw["auth"] != "none":
                        lines.append("250-AUTH PLAIN")
                    lines.append("250 8BITMIME")
                    for x in lines:
                        c.send(x)
                elif u.startswith("STARTTLS"):
                    if kw["tls"] != "starttls":
                        c.send("502 not supported")
                        continue
                    c.send("220 go ahead")
                    try:
                        s = self._ctx().wrap_socket(s, server_side=True)
                    except (ssl.SSLError, OSError) as e:
                        self.events.append(("tls-handshake-failed", type(e).__name__))
                        return
                    c = Conn(s)
                    tls_done = True
                elif u.startswith("AUTH"):
                    parts = l.split(" ")
                    raw = base64.b64decode(parts[2]).split(b"\0") if len(parts) > 2 else []
                    user = raw[1].decode() if len(raw) > 1 else ""
                    pw = raw[2].decode() if len(raw) > 2 else ""
                    self.auth_attempts.append((user, pw, tls_done))
                    if kw["auth"] == "reject":
                        c.send(f"535 5.7.8 Authentication failed for user {user} password {pw}")
                    else:
                        c.send("235 2.7.0 ok")
                elif u.startswith("MAIL FROM"):
                    if kw["silent"] == "after_mailfrom":
                        time.sleep(60)
                        return
                    self.events.append(("mailfrom", l))
                    c.send("250 ok")
                elif u.startswith("RCPT TO"):
                    self.events.append(("rcpt", l))
                    if kw["rcpt"] == "reject":
                        c.send(f"550 5.1.1 no such mailbox {l[8:]}")
                    else:
                        c.send("250 ok")
                elif u == "DATA":
                    c.send("354 go")
                    if kw["data"] == "drop_mid":
                        c.s.recv(200)
                        s.close()
                        return
                    body = c.until(b"\r\n.\r\n")
                    self.messages.append(body)
                    if kw["data"] == "drop_after_full":
                        s.close()
                        return
                    if kw["data"] == "error":
                        c.send("554 5.6.0 rejected, saw credentials in message")
                        continue
                    c.send("250 queued")
                elif u == "RSET":
                    c.send("250 ok")
                elif u == "QUIT":
                    c.send("221 bye")
                    return
                else:
                    c.send("500 unknown")
        except (EOFError, OSError, ssl.SSLError, ValueError) as e:
            self.errors.append(type(e).__name__)
        finally:
            try:
                s.close()
            except OSError:
                pass
