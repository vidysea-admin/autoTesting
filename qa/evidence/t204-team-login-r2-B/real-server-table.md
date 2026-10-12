# AU20 real-server table (coordinator B, cycle 2)

Real `python -m uvicorn autotester.ui.app:app` processes on loopback/LAN ports 18500+, throwaway data dirs, AUTOTESTER_HOSTED=1 unless row says otherwise. LAN row binds use the machine's own non-loopback address 192.168.1.4 (and 172.22.0.1). Probe = GET /auth/login with the Host a browser at that origin sends, and a login POST with that Host + Origin; cell is `GET/POST` status (200/303 = served, 403 = guard refusal). A raised row is probed in-process (no lifespan) to learn what the guard WOULD serve.

| row | bind args | startup | probes (scheme GET/POST) | expectation met |
|---|---|---|---|---|
| c01-lan-hosts-bare-custom-port | `--host 192.168.1.4 --port 18500` ALLOWED_HOSTS=192.168.1.4 | raised (guard probe) | h:403/403 h:403/403 | yes |
| c02-lan-origin-https-bare-custom-port | `--host 192.168.1.4 --port 18501` ALLOWED_ORIGINS=https://192.168.1.4 | raised (guard probe) | h:403/403 h:403/403 | yes |
| c03-lan-hosts-with-port-no-origin | `--host 192.168.1.4 --port 18502` ALLOWED_HOSTS=192.168.1.4:18502 | raised (guard probe) | h:200/403 h:200/403 | yes |
| c04-lan-origin-http-port | `--host 192.168.1.4 --port 18503` ALLOWED_ORIGINS=http://192.168.1.4:18503 | started | h:200/303 h:200/403 | yes |
| c05-lan-origin-https-port | `--host 192.168.1.4 --port 18504` ALLOWED_ORIGINS=https://192.168.1.4:18504 | started | h:200/403 h:200/303 | yes (scheme question) |
| c06-lan-hosts-and-origin | `--host 192.168.1.4 --port 18505` ALLOWED_HOSTS=192.168.1.4:18505 ALLOWED_ORIGINS=http://192.168.1.4:18505 | started | h:200/303 h:200/403 | yes |
| c07-lan-wrong-port-in-origin | `--host 192.168.1.4 --port 18506` ALLOWED_ORIGINS=http://192.168.1.4:1 | raised (guard probe) | h:403/403 h:403/403 | yes |
| c08-lan-other-host-listed | `--host 192.168.1.4 --port 18507` ALLOWED_HOSTS=at.example ALLOWED_ORIGINS=https://at.example | raised (guard probe) | h:403/403 h:403/403 | yes |
| c09-lan-eq-form | `--host=192.168.1.4 --port=18508` ALLOWED_ORIGINS=http://192.168.1.4:18508 | started | h:200/303 h:200/403 | yes |
| c10-lan-eq-form-bare-origin | `--host=192.168.1.4 --port=18509` ALLOWED_ORIGINS=http://192.168.1.4 | raised (guard probe) | h:403/403 h:403/403 | yes |
| c11-lan-uvicorn-port-env | `--host 192.168.1.4` UVICORN_PORT=18510 ALLOWED_ORIGINS=http://192.168.1.4:18510 | started | h:200/303 h:200/403 | yes |
| c12-lan-uvicorn-port-env-origin-8000 | `--host 192.168.1.4` UVICORN_PORT=18511 ALLOWED_ORIGINS=http://192.168.1.4:8000 | raised (guard probe) | h:403/403 h:403/403 | yes |
| c13-lan-argv-port-beats-env | `--host 192.168.1.4 --port 18512` UVICORN_PORT=9 ALLOWED_ORIGINS=http://192.168.1.4:18512 | started | h:200/303 h:200/403 | yes |
| c14-lan-repeated-host-last-wins | `--host 10.9.9.9 --host 192.168.1.4 --port 18513` ALLOWED_ORIGINS=http://192.168.1.4:18513 | started | h:200/303 h:200/403 | yes |
| c15-lan-repeated-port-last-wins | `--host 192.168.1.4 --port 1 --port 18514` ALLOWED_ORIGINS=http://192.168.1.4:18514 | started | h:200/303 h:200/403 | yes |
| c16-lan-repeated-port-same | `--host 192.168.1.4 --port 18515 --port 18515` ALLOWED_ORIGINS=http://192.168.1.4:18515 | started | h:200/303 h:200/403 | yes |
| c17-second-lan-addr | `--host 172.22.0.1 --port 18516` ALLOWED_ORIGINS=http://172.22.0.1:18516 | started | h:200/303 h:200/403 | yes |
| c18-lan-hosts-star-only | `--host 192.168.1.4 --port 18517` ALLOWED_HOSTS=* | raised (guard probe) | h:403/403 h:403/403 | yes |
| c19-lan-lists-comma-blank | `--host 192.168.1.4 --port 18518` ALLOWED_ORIGINS=, ALLOWED_HOSTS=  | raised (guard probe) | h:403/403 h:403/403 | yes |
| c20-lan-star-plus-real-entry | `--host 192.168.1.4 --port 18519` ALLOWED_ORIGINS=*,http://192.168.1.4:18519 | started | h:200/303 h:200/403 | yes |
| c21-lan-origin-caps-slash | `--host 192.168.1.4 --port 18520` ALLOWED_ORIGINS=HTTP://192.168.1.4:18520/ | started | h:200/303 h:200/403 | yes |
| c22-lan-origins-space-separated | `--host 192.168.1.4 --port 18521` ALLOWED_ORIGINS=https://x.example http://192.168.1.4:18521 | started | h:200/303 h:200/403 | yes |
| l01-127.0.0.1-foreign-list | `--host 127.0.0.1 --port 18522` ALLOWED_HOSTS=at.example | started | h:200/303 h:200/303 | yes |
| l02-127.0.0.2-foreign-list | `--host 127.0.0.2 --port 18523` ALLOWED_HOSTS=at.example | raised (guard probe) | h:403/403 h:403/403 | yes |
| l03-127.0.0.2-origin-listed | `--host 127.0.0.2 --port 18524` ALLOWED_ORIGINS=http://127.0.0.2:18524 | started | h:200/303 h:200/403 | yes |
| l04-localhost-foreign-list | `--host localhost --port 18525` ALLOWED_HOSTS=at.example | started | h:200/303 h:200/303 | yes |
| l05-localhost-port-env | `--host localhost` UVICORN_PORT=18526 ALLOWED_HOSTS=at.example | started | h:200/303 h:200/303 | yes |
| l06-localhost-eq-form | `--host=localhost --port=18527` ALLOWED_ORIGINS=https://at.example | started | h:200/303 h:200/303 | yes |
| l07-ipv6-loopback | `--host ::1 --port 18528` ALLOWED_HOSTS=at.example | started | h:200/303 h:200/303 | yes |
| l08-loopback-star-only-list | `--host 127.0.0.1 --port 18529` ALLOWED_HOSTS=* | raised (guard probe) | h:200/303 h:200/303 | yes |
| l09-loopback-no-list | `--host 127.0.0.1 --port 18530`  | raised (guard probe) | h:200/303 h:200/303 | yes |
| l10-loopback-uppercase-LOCALHOST | `--host LOCALHOST --port 18531` ALLOWED_HOSTS=at.example | started | h:200/303 h:200/303 | yes |
| l11-repeated-wild-then-loop | `--host 0.0.0.0 --host 127.0.0.1 --port 18532` ALLOWED_HOSTS=at.example | started | h:200/303 h:200/303 | yes |
| w01-wild4-missing-public | `--host 0.0.0.0 --port 18533` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com | raised (guard probe) | h:200/303 | yes |
| w02-wild4-public-right | `--host 0.0.0.0 --port 18534` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com | started | h:200/303 | yes |
| w03-wild6-public-right | `--host :: --port 18535` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com | started | h:200/303 | yes |
| w04-wild6-missing-public | `--host :: --port 18536` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com | raised (guard probe) | h:200/303 | yes |
| w05-wild4-public-bare-host | `--host 0.0.0.0 --port 18537` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=qa.example.com | raised (guard probe) | h:200/303 | yes |
| w06-wild4-public-ftp | `--host 0.0.0.0 --port 18538` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=ftp://qa.example.com | raised (guard probe) | h:200/303 | yes |
| w07-wild4-public-path | `--host 0.0.0.0 --port 18539` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com/app | raised (guard probe) | h:200/303 | yes |
| w08-wild4-public-bad-port | `--host 0.0.0.0 --port 18540` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com:abc | raised (guard probe) | h:200/303 | yes |
| w09-wild4-public-no-host | `--host 0.0.0.0 --port 18541` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https:// | raised (guard probe) | h:200/303 | yes |
| w10-wild4-public-userinfo | `--host 0.0.0.0 --port 18542` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://me@qa.example.com | raised (guard probe) | h:200/303 | yes |
| w11-wild4-public-star | `--host 0.0.0.0 --port 18543` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=* | raised (guard probe) | h:200/303 | yes |
| w12-wild4-public-blank | `--host 0.0.0.0 --port 18544` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=    | raised (guard probe) | h:200/303 | yes |
| w13-wild4-public-wrong-host | `--host 0.0.0.0 --port 18545` ALLOWED_HOSTS=other.example.com ALLOWED_ORIGINS=https://other.example.com PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:403/403 | yes |
| w14-wild4-public-wrong-port | `--host 0.0.0.0 --port 18546` ALLOWED_ORIGINS=https://qa.example.com:8443 PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:403/403 | yes |
| w15-wild4-public-wrong-scheme | `--host 0.0.0.0 --port 18547` ALLOWED_ORIGINS=http://qa.example.com PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:200/403 | yes |
| w16-wild4-public-hosts-only | `--host 0.0.0.0 --port 18548` ALLOWED_HOSTS=qa.example.com PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:200/403 | yes |
| w17-wild4-public-origins-only | `--host 0.0.0.0 --port 18549` ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com | started | h:200/303 | yes |
| w18-wild4-public-explicit-443 | `--host 0.0.0.0 --port 18550` ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com:443 | started | h:200/303 | yes |
| w19-wild4-public-caps-slash | `--host 0.0.0.0 --port 18551` ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=HTTPS://QA.Example.com/ | started | h:200/303 | yes |
| w20-wild4-public-lan-http | `--host 0.0.0.0 --port 18552` ALLOWED_ORIGINS=http://192.168.1.4:18552 PUBLIC_ORIGIN=http://192.168.1.4:18552 | started | h:200/303 | yes |
| w21-wild4-public-lan-nonlisted-port | `--host 0.0.0.0 --port 18553` ALLOWED_ORIGINS=http://192.168.1.4:18553 PUBLIC_ORIGIN=http://192.168.1.4:1 | raised (guard probe) | h:200/303 | yes |
| w22-wild4-public-loopback | `--host 0.0.0.0 --port 18554` ALLOWED_HOSTS=at.example PUBLIC_ORIGIN=http://localhost:18554 | started | h:200/303 | yes |
| w23-wild4-eq-form-missing | `--host=0.0.0.0 --port=18555` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com | raised (guard probe) | h:200/303 | yes |
| w24-wild4-eq-form-public | `--host=0.0.0.0 --port=18556` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com | started | h:200/303 | yes |
| w25-loop-then-wild-repeated | `--host 127.0.0.1 --host 0.0.0.0 --port 18557` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com | raised (guard probe) | h:200/303 | yes |
| w26-env-UVICORN_HOST-wild-missing | `--port 18558` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com UVICORN_HOST=0.0.0.0 | raised (guard probe) | h:200/303 | yes |
| w27-env-UVICORN_HOST-wild-public | `--port 18559` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com UVICORN_HOST=0.0.0.0 PUBLIC_ORIGIN=https://qa.example.com | started | h:200/303 | yes |
| w28-wild4-star-list-public-ok | `--host 0.0.0.0 --port 18560` ALLOWED_HOSTS=* PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:403/403 | yes |
| w29-wild4-comma-list-public-ok | `--host 0.0.0.0 --port 18561` ALLOWED_ORIGINS=, PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:403/403 | yes |
| w30-wild4-blank-list | `--host 0.0.0.0 --port 18562` PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:403/403 | yes |
| w31-wild4-star-plus-entry | `--host 0.0.0.0 --port 18563` ALLOWED_ORIGINS=*,https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com | started | h:200/303 | yes |
| w32-odd-wildcard-host-0 | `--host 0 --port 18564` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com | raised (guard probe) | h:200/303 | yes (uvicorn binds '0' as every IPv4 address; the code sees a concrete host '0') |
| w33-odd-wildcard-host-0-listed | `--host 0 --port 18565` ALLOWED_ORIGINS=http://0:18565 | raised (guard probe) | h:200/303 | yes (operator lists '0'; the real server binds every address and no public origin is required) |
| w34-odd-wildcard-ipv6-long | `--host 0:0:0:0:0:0:0:0 --port 18566` ALLOWED_HOSTS=qa.example.com ALLOWED_ORIGINS=https://qa.example.com | raised (guard probe) | h:200/303 | yes (long-form wildcard) |
| p01-lan-public-admitted | `--host 192.168.1.4 --port 18567` ALLOWED_ORIGINS=http://192.168.1.4:18567 https://qa.example.com PUBLIC_ORIGIN=https://qa.example.com | started | h:200/303 h:200/303 | yes |
| p02-lan-public-not-admitted | `--host 192.168.1.4 --port 18568` ALLOWED_ORIGINS=http://192.168.1.4:18568 PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:200/303 h:403/403 | yes |
| p03-lan-public-malformed | `--host 192.168.1.4 --port 18569` ALLOWED_ORIGINS=http://192.168.1.4:18569 PUBLIC_ORIGIN=qa.example.com | raised (guard probe) | h:200/303 | yes |
| p04-loop-public-not-admitted | `--host 127.0.0.1 --port 18570` ALLOWED_HOSTS=at.example PUBLIC_ORIGIN=https://qa.example.com | raised (guard probe) | h:200/303 h:403/403 | yes |
| p05-loop-no-public | `--host 127.0.0.1 --port 18571` ALLOWED_HOSTS=at.example | started | h:200/303 | yes |
| n01-not-hosted-wild | `--host 0.0.0.0 --port 18572`  | started | h:200/303 | yes |
| n02-not-hosted-loop | `--host 127.0.0.1 --port 18573`  | started | h:200/303 | yes |
| n03-hosted-auth-disabled | `--host 127.0.0.1 --port 18574` AUTH_DISABLED=1 ALLOWED_HOSTS=at.example | raised (guard probe) | h:200/303 | yes |
| w35-compose-default-localhost-wrong-lists | `--host 0.0.0.0 --port 18575` ALLOWED_HOSTS=wrong.example ALLOWED_ORIGINS=http://wrong.example:18575 PUBLIC_ORIGIN=https://localhost | started | h:403/403 | NO (see verdict) (what compose.prod.yml passes when neither AUTOTESTER_PUBLIC_ORIGIN nor AUTOTESTER_DOMAIN is set; the lists do not name the server) |
| w36-compose-default-localhost-no-lists-naming-server | `--host 0.0.0.0 --port 18576` ALLOWED_ORIGINS=https://other.example PUBLIC_ORIGIN=https://localhost | started | h:403/403 | NO (see verdict) (same, origin list names another host) |
| w37-loopback-public-http-localhost-explicit | `--host 0.0.0.0 --port 18577` ALLOWED_ORIGINS=https://other.example PUBLIC_ORIGIN=http://localhost:18577 | started | h:403/403 | NO (see verdict) (operator sets a loopback public origin on a wildcard bind; real users arrive by LAN) |

78 rows; rows not meeting expectation: 3 (w35-w37, the compose-default `https://localhost` public origin: started although the lists do not name the server, every request 403).

Reading: concrete/loopback rows c01-c22, l01-l11 agree with the guards (raise iff no scheme is fully served; a started row serves GET 200 + POST 303 for at least one scheme). c05 (https-only origin on a plain-http bind) starts and a direct http browser POST is 403 (low, PROPOSED-ISSUE). Wildcard rows w01-w34 raise exactly as owner option A requires (missing/malformed/not-admitted AUTOTESTER_PUBLIC_ORIGIN) and start when it is admitted. w33: `--host 0` is not in _WILDCARD; on Windows uvicorn then fails to bind (getaddrinfo), on Linux it would bind all addresses (low).