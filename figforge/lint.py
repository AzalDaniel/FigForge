"""Flag email-client robustness hazards in HTML.

Every rule here is a lesson paid for in this project's debugging. Email clients
(Outlook's Word engine, Gmail's sanitiser) silently ignore or rewrite CSS that
browsers honour; these checks catch the patterns that *looked* fine in an
in-app/preview render but broke once actually emailed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Finding:
    rule: str
    severity: str  # "high" | "medium" | "low"
    line: int
    message: str
    suggestion: str

    def __str__(self):
        return (
            f"[{self.severity.upper()}] L{self.line} {self.rule} — {self.message}\n"
            f"        fix: {self.suggestion}"
        )


# Each rule: (id, severity, regex, message, suggestion, css_hazard). ``css_hazard``
# rules are skipped inside <!--[if mso]> ... <![endif]--> blocks, where Outlook's
# VML boilerplate legitimately uses display:inline-block etc. The regex runs per
# line so findings carry a line number (img-without-width is handled separately
# because <img> tags can span lines).
_RULES = [
    (
        "background-size-cover",
        "high",
        re.compile(r"background-size\s*:\s*cover", re.I),
        "background-size:cover is unsupported in Outlook (Word) and unreliable in "
        "Gmail; the image gets shown at native size / cropped differently per client.",
        "Bake the background + foreground into one flat <img> sized with a width "
        "attribute, or use a VML <v:rect fill> fallback for Outlook.",
        False,
    ),
    (
        "inline-block-banner",
        "high",
        re.compile(r"style\s*=\s*['\"][^'\"]*display\s*:\s*inline-block", re.I),
        "display:inline-block on a wrapper shrink-wraps to content width; a "
        "width:100% child (e.g. a full-bleed banner) then never reaches the email "
        "width, leaving a gap.",
        "Use display:block;width:100% on the wrapper, or give the inner table a "
        'fixed pixel width (e.g. width="680").',
        True,
    ),
    (
        "base64-image",
        "high",
        re.compile(r"src\s*=\s*['\"]?data:image", re.I),
        "Base64 (data:) images are stripped by Gmail and bloat the HTML toward "
        "Gmail's ~102 KB clip limit.",
        "Host the image and reference it by absolute https URL.",
        False,
    ),
    (
        "position-absolute",
        "medium",
        re.compile(r"position\s*:\s*(absolute|fixed)", re.I),
        "position:absolute/fixed is dropped by most email clients; overlapping "
        "layers won't stack as intended.",
        "Lay out with tables; bake overlapping art into a single image.",
        True,
    ),
    (
        "flex-or-grid",
        "medium",
        re.compile(r"display\s*:\s*(flex|grid|inline-flex|inline-grid)", re.I),
        "Flexbox/Grid are unsupported in Outlook and patchy elsewhere.",
        "Use table-based layout for email.",
        True,
    ),
    (
        "webfont-no-fallback",
        "low",
        re.compile(r"font-family\s*:\s*([^;\"']+)", re.I),
        "font-family should end in a generic fallback; many clients won't load the "
        "web font and need Arial/Helvetica/sans-serif.",
        "Append a web-safe fallback, e.g. 'Archivo, Arial, Helvetica, sans-serif'.",
        True,
    ),
]

# rules that only fire when something extra is true (checked in code, not regex)
_FALLBACK_FAMILIES = (
    "arial",
    "helvetica",
    "sans-serif",
    "serif",
    "georgia",
    "times",
    "verdana",
    "tahoma",
    "courier",
    "monospace",
)


def _mask_plain_comments(html: str) -> str:
    """Blank the *contents* of ordinary <!-- --> comments (keep the markers and
    newlines so line numbers stay stable) so commentary like "use a single <img>"
    isn't linted. Outlook conditional comments (<!--[if ...]>) are left intact."""

    def repl(m):
        body = m.group(0)
        if re.match(r"<!--\s*\[if", body, re.I):
            return body
        return re.sub(r"[^\n]", " ", body)

    return re.sub(r"<!--.*?-->", repl, html, flags=re.S)


def _mso_line_ranges(lines):
    """Line numbers (1-based) that fall inside <!--[if ...mso...]> ... <![endif]-->."""
    inside, ranges = False, set()
    for i, line in enumerate(lines, 1):
        if re.search(r"<!--\[if[^>]*mso", line, re.I):
            inside = True
        if inside:
            ranges.add(i)
        if "<![endif]-->" in line:
            inside = False
    return ranges


def lint_html(html: str) -> list:
    """Return a list of :class:`Finding` for an HTML string (or file contents)."""
    findings = []
    html = _mask_plain_comments(html)
    lines = html.splitlines()
    mso = _mso_line_ranges(lines)

    for i, line in enumerate(lines, 1):
        for rid, sev, rx, msg, fix, css_hazard in _RULES:
            if css_hazard and i in mso:
                continue  # VML boilerplate legitimately uses these inside [if mso]
            for m in rx.finditer(line):
                if rid == "webfont-no-fallback":
                    fam = m.group(1).lower()
                    if any(f in fam for f in _FALLBACK_FAMILIES):
                        continue
                findings.append(Finding(rid, sev, i, msg, fix))
                break  # one finding per rule per line is enough

    # img-without-width: scan whole-text because <img> tags can span lines.
    for m in re.finditer(r"<img\b[^>]*>", html, re.I | re.S):
        tag = m.group(0)
        if not re.search(r"\bwidth\s*=", tag, re.I):
            ln = html.count("\n", 0, m.start()) + 1
            findings.append(
                Finding(
                    "img-without-width",
                    "medium",
                    ln,
                    "An <img> without a width attribute is sized unpredictably across "
                    "clients (esp. Outlook, which ignores CSS width on some images).",
                    'Add an explicit width="N" attribute matching the CSS width.',
                )
            )

    # document-level: background-image on an element with no Outlook VML fallback
    has_vml = bool(re.search(r"v:rect|behavior:\s*url\(#default#VML\)", html, re.I))
    if re.search(r"background-image\s*:\s*url", html, re.I) and not has_vml:
        bg_line = next(
            (
                i
                for i, text in enumerate(html.splitlines(), 1)
                if re.search(r"background-image\s*:\s*url", text, re.I)
            ),
            0,
        )
        findings.append(
            Finding(
                "bgimage-no-vml",
                "high",
                bg_line,
                "CSS background-image with no VML fallback won't render in Outlook "
                "(Word engine).",
                "Add an <!--[if mso]><v:rect ... fill> fallback, or bake the art into "
                "a foreground <img>.",
            )
        )

    findings.sort(
        key=lambda f: ({"high": 0, "medium": 1, "low": 2}[f.severity], f.line)
    )
    return findings
