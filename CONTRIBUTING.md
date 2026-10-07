# Contributing

Contributions that improve defensive usefulness, deterministic behavior,
diagnostics, documentation, and test coverage are welcome.

1. Open an issue for behavior changes that affect normalization or output.
2. Keep the runtime dependency-free unless there is a compelling, reviewed
   security or correctness reason.
3. Use only synthetic fixtures: reserved `.test` domains, RFC 5737 TEST-NET
   IPv4 addresses, RFC 3849 documentation IPv6 addresses, and invented hashes.
4. Do not add code that visits, resolves, executes, or automatically refangs an
   indicator.
5. Add tests and run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
6. Document any output-schema or normalization change.

Security vulnerabilities should follow [SECURITY.md](SECURITY.md) instead of
the public issue workflow.
