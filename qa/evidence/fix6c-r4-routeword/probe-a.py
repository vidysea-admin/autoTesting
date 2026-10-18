from autotester.schema.leak_evidence import validate_url_template, segment_is_id_like, ROUTE_WORDS
from autotester.stages.leak_evidence import templatise_url
new = "cart fast inbox item items mail me quiz quizzes slow status".split()
print("new words all in set:", all(w in ROUTE_WORDS for w in new), "n_added_vs_base_expected 11")
refuse = ["/inbox/alice", "/inbox/zorblax-quimby", "/mail/jane.doe", "/me/9f8a7c6b5d4e3f2a1b0c", "/status/eyJhbGciOiJIUzI1NiJ9",
 "/items/12345", "/quiz/507f1f77bcf86cd799439011", "/inbox/jane.doe%40x.com", "/inbox/jane.doe@x.com", "/mail/550e8400-e29b-41d4-a716-446655440000",
 "/inbox/bob", "/cart/cus_9s6XKzkNRiz8i3", "/me-alice", "/status/acme-corp", "/users/me/alice", "/inbox/ABCDEFGHIJKLMNOPQRSTUVWXYZ", "/mail/+14155550123", "/inbox/Alice", "/ME/Alice"]
for u in refuse:
    try: validate_url_template(u); print("ACCEPTED(BAD?)", u)
    except ValueError as e: print("refused ", u)
keep = ["/api/me", "/api/Status", "/inbox", "/mail/{id}", "/quiz/{id}/items/{id}", "/api/fast", "/cart/{id}"]
for u in keep:
    try: print("kept    ", validate_url_template(u))
    except ValueError as e: print("REFUSED(BAD?)", u)
for u in ["https://x.test/inbox/alice?token=abc&q=Zorblax", "https://x.test/me/9f8a7c6b5d4e3f2a", "https://x.test/status/acme-corp/members/42", "https://x.test/mail/alice@x.com", "https://x.test/users/me", "https://x.test/quiz/Zx9secret?next=/inbox/bob"]:
    print("templatise", u, "->", templatise_url(u))
