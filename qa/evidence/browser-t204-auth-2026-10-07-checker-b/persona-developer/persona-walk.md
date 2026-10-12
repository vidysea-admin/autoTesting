| screen | what they tried | what blocked them | severity |
|---|---|---|---|
| waiting page | after signup | waiting page, no user list, all URLs 403 | secure |
| / after Developer group | next click | reaches Projects in 1 click; no Users/Groups links | pass |
| nav | Settings link | 403 dead link | Low |
| /onboard | create devproj (own) | form fields have visible text but no <label> association; credential fields placeholder only | Low |
| /projects/devproj/env | read sentinel secret | set/not set only; value absent from source; no Show toggle | secure |
| disable/enable/delete | next click after disable | redirected to login; same message as wrong password | pass |
