# Security Policy

## Supported versions

figforge is pre-1.0; security fixes are made against the latest release on PyPI
and `main`.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, report
privately via GitHub:
[**Report a vulnerability**](https://github.com/AzalDaniel/FigForge/security/advisories/new).

We'll acknowledge within a few days and keep you updated through to a fix and
disclosure.

## Scope notes

figforge parses untrusted SVG/HTML. It uses Python's standard `xml.etree`
parser (not a hardened one) and, for the optional `render` extras, hands SVG/HTML
to `cairosvg`/`weasyprint`. Treat input files as untrusted: run rasterising and
rendering on inputs you control, and be aware that SVG/XML can reference external
resources. Reports about parser resource-exhaustion or SSRF-style external-entity
fetching in these paths are in scope and welcome.
