| screen | what they tried | what blocked them | severity |
|---|---|---|---|
| login -> / | sign in, reach shared projects | nothing; 1 click; only Alpha listed (no dedicated shared-with-me page exists yet, T-197+) | Info |
| / | find what they can do | + New project (x3), Live view, Settings links shown; /onboard /live /settings return 403 | Medium (dead-end controls) |
| /projects/alpha | open shared project | page shows Credentials, Project settings, Add case, Teach it, Watch live buttons although tester only views; /env /edit /access render 200 | Medium |
| /projects/alpha/env | read credentials | shows set/not set only, sentinel absent; POST to env, env/add, env/url, edit, access via crafted fetch all 403 | secure |
| /projects/alpha/access | see who has access | tester can read the list incl. lead@example.com (other people's emails) | Medium |
| /projects/beta (unshared) vs /projects/doesnotexist | probe | identical 404 page | secure |
