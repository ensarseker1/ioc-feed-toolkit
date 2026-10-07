# Security policy

## Supported versions

Until the first tagged release, security fixes are applied to the `main` branch.
After releases begin, this section will identify supported release lines.

## Reporting a vulnerability

Please use GitHub's **Report a vulnerability** option in the repository Security
tab so details remain private. Do not include exploit details, sensitive feed
contents, or live credentials in a public issue.

Include the affected version or commit, operating system and Python version,
minimal reproduction steps using synthetic indicators, expected behavior, and
the security impact. Maintainers aim to acknowledge a complete report within
five business days, provide a preliminary assessment after reproduction, and
coordinate disclosure when a fix is available. These are response goals, not a
guarantee of bounty eligibility or compensation.

## Security boundaries

IOC Feed Toolkit is designed to parse local user-provided text as data. It must
not resolve domains, contact IPs, request URLs, execute indicators, load plugins
from a feed, or automatically refang disguised values. A change that adds
network access or input execution is outside the default threat model and must
be explicit, opt-in, documented, and separately reviewed.

Useful reports include parser crashes on bounded input, validation bypasses,
path or output-file vulnerabilities, CSV injection bypasses, nondeterministic
provenance loss, resource-exhaustion issues within documented limits, and
packaging or CI supply-chain concerns.

Reports that only show an indicator is reachable or malicious are not product
vulnerabilities. Never visit a submitted indicator solely to validate a report.
