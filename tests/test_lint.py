from figforge import lint_html


def test_catches_classic_bugs():
    bad = (
        '<a style="text-decoration:none;display:inline-block">'
        '<table style="width:100%"></table></a>\n'
        '<td style="background-image:url(x);background-size:cover"></td>\n'
        '<img src="data:image/png;base64,AAAA"/>\n'
        '<img src="logo.png">'
    )
    rules = {f.rule for f in lint_html(bad)}
    assert {
        "inline-block-banner",
        "background-size-cover",
        "base64-image",
        "img-without-width",
    } <= rules


def test_clean_email_passes():
    good = (
        '<table width="680"><tr><td>'
        '<img src="https://cdn/x.png" width="100"/></td></tr></table>'
    )
    assert lint_html(good) == []


def test_ignores_mso_block_and_comments():
    # display:inline-block here is legit Outlook VML boilerplate; the <img> is
    # only mentioned inside a comment.
    h = (
        "<!--[if mso]><style>v\\:*{display:inline-block}</style><![endif]-->\n"
        '<!-- prefer a single <img> here --><table width="680"></table>'
    )
    assert lint_html(h) == []
