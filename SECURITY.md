# Security Policy

memU handles user-provided content, memory records, embeddings, local files, and
provider credentials. Please report security concerns privately so maintainers
can investigate before details become public.

## Supported Versions

Security fixes are prioritized for:

- the latest released `memu-py` version
- the `main` branch when a fix has not been released yet

Older releases may receive fixes when the issue is severe and the patch can be
backported safely.

## Reporting a Vulnerability

Do not open a public GitHub issue for suspected vulnerabilities.

Email reports to [contact@nevamind.ai](mailto:contact@nevamind.ai) with:

- affected version or commit
- operating system and deployment mode
- reproduction steps or proof of concept
- expected impact
- whether credentials, files, memory data, or external providers are involved

We aim to acknowledge reports within 2 business days and will share status
updates as we investigate. If a vulnerability is confirmed, maintainers will
coordinate a fix, release guidance, and public disclosure timing with the
reporter when possible.

## Scope

Useful reports include issues such as:

- unauthorized access to memory data across scopes or users
- unsafe handling of API keys, environment variables, or provider credentials
- path traversal, unintended file reads, or writes outside configured roots
- server endpoint authentication or authorization bypasses
- injection paths that can alter persistent memory without review

Out-of-scope reports include social engineering, spam, denial-of-service without
a concrete vulnerability, and findings that require access to accounts or
systems you do not own or have permission to test.

## Automated Scanning

Pull requests and the `main` branch are scanned with CodeQL for Python and Rust.
These checks complement code review and responsible disclosure; they do not
replace private reporting for suspected vulnerabilities.

## Safe Harbor

Good-faith research that avoids privacy violations, data destruction, service
disruption, and unauthorized access is welcome. Stop testing and contact us
privately if you encounter sensitive data or credentials.
