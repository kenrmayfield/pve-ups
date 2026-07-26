"""UI i18n consistency checks (regex-based, no JS engine needed).

Enforces: en.js and de.js define identical key sets, no duplicate keys, and every
key referenced from index.html (data-i18n* attributes) or app.js (literal t() calls)
exists in the English dictionary. Dynamic keys built at runtime ("theme." + mode,
"state.engine." + s, ...) are covered by the key-set checks on the dictionaries.
"""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "app" / "web"

# One dictionary entry per line:   "some.key": "..." / function
KEY_RE = re.compile(r'^\s*"([^"]+)":', re.MULTILINE)
# Literal t("key") / t('key') calls in app.js (not preceded by an identifier char).
T_CALL_RE = re.compile(r"""(?<![A-Za-z0-9_$])t\(\s*["']([^"']+)["']""")
# data-i18n, data-i18n-html, data-i18n-title, data-i18n-placeholder in index.html.
ATTR_RE = re.compile(r'data-i18n(?:-[a-z]+)*="([^"]+)"')


def dict_keys(fname: str) -> list[str]:
    return KEY_RE.findall((WEB / "i18n" / fname).read_text(encoding="utf-8"))


def test_dictionaries_have_no_duplicate_keys():
    for fname in ("en.js", "de.js"):
        keys = dict_keys(fname)
        dupes = {k for k in keys if keys.count(k) > 1}
        assert not dupes, f"{fname}: duplicate keys {sorted(dupes)}"


def test_dictionary_key_sets_are_identical():
    en, de = set(dict_keys("en.js")), set(dict_keys("de.js"))
    assert en == de, (
        f"missing in de.js: {sorted(en - de)}; missing in en.js: {sorted(de - en)}"
    )


def test_index_html_keys_exist_in_english_dictionary():
    en = set(dict_keys("en.js"))
    used = set(ATTR_RE.findall((WEB / "index.html").read_text(encoding="utf-8")))
    assert used, "no data-i18n* attributes found in index.html"
    assert used <= en, f"index.html references unknown keys: {sorted(used - en)}"


def test_placeholders_match_between_languages():
    # {name} placeholders must be the same set per key, or t() interpolation breaks
    # silently in one language.
    line_re = re.compile(r'^\s*"([^"]+)":(.*)$', re.MULTILINE)
    ph_re = re.compile(r"\{([a-z]+)\}")

    def placeholders(fname):
        text = (WEB / "i18n" / fname).read_text(encoding="utf-8")
        return {k: set(ph_re.findall(rest)) for k, rest in line_re.findall(text)}

    en, de = placeholders("en.js"), placeholders("de.js")
    for key in en.keys() & de.keys():
        assert en[key] == de[key], (
            f"{key}: placeholders differ (en={sorted(en[key])}, de={sorted(de[key])})"
        )


def test_app_js_keys_exist_in_english_dictionary():
    en = set(dict_keys("en.js"))
    src = (WEB / "app.js").read_text(encoding="utf-8")
    used = {k for k in T_CALL_RE.findall(src) if not k.endswith(".")}
    assert used, "no t() calls found in app.js"
    assert used <= en, f"app.js references unknown keys: {sorted(used - en)}"


def test_snmp_probe_status_keys_exist_in_both_dictionaries():
    """Every per-OID probe status the backend can emit needs a UI label in EN and DE."""
    from app.ups import PROBE_STATUSES

    en, de = set(dict_keys("en.js")), set(dict_keys("de.js"))
    missing = [
        f"snmp.st.{status}"
        for status in PROBE_STATUSES
        if f"snmp.st.{status}" not in en or f"snmp.st.{status}" not in de
    ]
    assert not missing, f"probe statuses without a dictionary entry: {missing}"


def test_selftest_interval_options_match_the_backend():
    """The <select> in index.html must offer exactly config.SELFTEST_INTERVALS.

    HTML and Python constant are the one place where the selectable intervals can drift
    apart; a value the backend does not accept would be snapped back to 1440 on save.
    """
    from app.config import SELFTEST_INTERVALS

    block = re.search(
        r'<select id="selftest_interval_min">(.*?)</select>',
        (WEB / "index.html").read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert block, "selftest_interval_min <select> not found in index.html"
    values = [int(v) for v in re.findall(r'value="(\d+)"', block.group(1))]
    assert values == list(SELFTEST_INTERVALS)
