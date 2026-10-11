from autotester.core.redact import mask_pii
t = "1. navigate https://x.test/\n2. fill phone = +91 98765 43210\n3. click Login\n4. fill a = 5"
print(repr(mask_pii(t)))
t = "1. fill phone = +44 20 7946 0958\n10. click b"
print(repr(mask_pii(t)))
t = "8. fill phone = 9876543210\n9. click b"
print(repr(mask_pii(t)))
