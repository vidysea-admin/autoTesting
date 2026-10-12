| screen | what they tried | what blocked them | severity |
|---|---|---|---|
| / (no project assigned) | find work | 'No projects yet - onboard your first one to get started' + 4 New project links; /onboard 403 | Medium (misleading dead-end CTA) |
| nav | admin controls | no Users/Groups links; /admin/* 403 | pass |
| / after alpha assigned | see projects | exactly /projects/alpha; beta, devproj 404 | pass |
| /projects/alpha/env | credentials | set/not set only, no sentinel | secure |
