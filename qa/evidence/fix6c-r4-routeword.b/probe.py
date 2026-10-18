from autotester.stages.leak_evidence import templatise_url
from autotester.schema.leak_evidence import validate_url_template, segment_is_id_like, LeakEvidence
cases = [
 "/inbox/alice", "/inbox/zorblax-quimby", "/mail/alice@x.com", "/mail/4821", "/mail/9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c",
 "/quiz/507f1f77bcf86cd799439011", "/me", "/users/me", "/users/Me/orders", "/status", "/api/status/ab12",
 "/inbox/jsmith", "/item/jsmith", "/cart/sk_live_abc", "/me/john.doe", "/api/items/%7Bid%7D", "/inbox/{id}",
 "/inbox/Inbox", "/QUIZ/x", "/status/me/mail/cart", "//inbox", "/inbox?user=alice&token=Zx9", "/inbox;alice", "/mail%2Falice",
 "/inbox/alice.smith", "/ME", "/inbox/%61lice",
]
for c in cases:
    t = templatise_url(c)
    try:
        v = validate_url_template(c); r="ACCEPT"
    except ValueError as e:
        r="REFUSE"
    print(f"{c!r:50} templ={t!r:40} validate={r}")
