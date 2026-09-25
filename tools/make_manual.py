"""Build the synthetic HO-3 rating manual PDF for the fictional carrier.

Purpose: render manual/example_mutual_ho3_rating_manual.pdf, the "filed" rating
manual that people and IBM Bob cite when they decide spreadsheet anomalies.
Every rate table in the PDF is rendered from build/rate_tables.json (extracted
from the workbook), so the manual and the workbook share one set of numbers.
The rule wording (R-100 ... R-900) lives in this module and follows plan 5.3.

Output is deterministic: reportlab invariant mode, fixed creation date, fixed
metadata, standard (non-embedded) fonts. Usage:

    python -m tools.make_manual            # build and self-check
    python -m tools.make_manual --no-check # build only

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md.
"""
import argparse
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLES = ROOT / "build" / "rate_tables.json"
DEFAULT_OUT = ROOT / "manual" / "example_mutual_ho3_rating_manual.pdf"

CARRIER = "Example Mutual Insurance Co. (FICTIONAL)"
EDITION = "2026-10"
TITLE = f"{CARRIER} — Homeowners HO-3 Rating Manual, Edition {EDITION}"
BANNER = "FICTIONAL — all names, rates and rules invented for a software demonstration"
PDF_DATE = "D:20261001000000+00'00'"  # fixed creation/modification date

INK = colors.HexColor("#1F2A44")
RULE_GREY = colors.HexColor("#9AA3B2")
SHADE = colors.HexColor("#E8ECF3")

# ---------------------------------------------------------------- styles

_base = getSampleStyleSheet()
BODY = ParagraphStyle("Body", parent=_base["BodyText"], fontName="Helvetica",
                      fontSize=10.5, leading=14.5, spaceAfter=6)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=9, leading=12, spaceAfter=4)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=9.5, leading=11, spaceAfter=0)
SECTION = ParagraphStyle("Section", parent=BODY, fontName="Helvetica-Bold", fontSize=15,
                         leading=19, textColor=INK, spaceBefore=4, spaceAfter=10)
RULE = ParagraphStyle("Rule", parent=BODY, fontName="Helvetica-Bold", fontSize=12,
                      leading=15, textColor=INK, spaceBefore=10, spaceAfter=6)
CAPTION = ParagraphStyle("Caption", parent=BODY, fontName="Helvetica-Bold", fontSize=9.5,
                         leading=12, spaceBefore=6, spaceAfter=3)
STEP = ParagraphStyle("Step", parent=BODY, leftIndent=22, firstLineIndent=-16, spaceAfter=3)
TOC_LEVELS = [
    ParagraphStyle("TOC0", parent=BODY, fontName="Helvetica-Bold", fontSize=10, leading=13,
                   spaceBefore=4, spaceAfter=0),
    ParagraphStyle("TOC1", parent=BODY, fontSize=10, leading=13, leftIndent=18, spaceAfter=0),
]

# ---------------------------------------------------------------- formatting


def num(x, places=None):
    """Plain number with thousands separators; trims to `places` if given."""
    if places is not None:
        return f"{x:,.{places}f}"
    if float(x).is_integer():
        return f"{int(x):,}"
    return f"{x:,}"


def money(x):
    """Whole dollars as $1,234, otherwise $1,234.56."""
    return "$" + (f"{int(x):,}" if float(x).is_integer() else f"{x:,.2f}")


def factor(x):
    """Rating factor with at least two decimals (0.66, 1.00, 1.125)."""
    text = repr(float(x))
    decimals = len(text.split(".")[1]) if "." in text else 0
    return f"{x:.{max(2, decimals)}f}"


def pct(x):
    """Percentage without float noise: 0.013 -> 1.3%, 0.25 -> 25%."""
    value = round(x * 100, 6)
    return (f"{int(value)}" if value.is_integer() else f"{value:g}") + "%"


# ---------------------------------------------------------------- building blocks


def para(text, style=BODY):
    return Paragraph(text, style)


def rule_head(rule_id, title):
    """Rule heading; also feeds the table of contents."""
    p = Paragraph(f"{rule_id}&nbsp;&nbsp;{title}", RULE)
    p.toc_entry = (1, f"{rule_id}  {title}")
    return p


def section_head(title):
    p = Paragraph(title, SECTION)
    p.toc_entry = (0, title)
    return p


def grid(header, rows, widths, caption=None):
    """A ruled table with a shaded header row, kept on one page."""
    data = [[Paragraph(f"<b>{h}</b>", CELL) for h in header]]
    data += [[Paragraph(str(c), CELL) for c in row] for row in rows]
    table = Table(data, colWidths=[w * inch for w in widths], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SHADE),
        ("GRID", (0, 0), (-1, -1), 0.5, RULE_GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    parts = [Paragraph(caption, CAPTION)] if caption else []
    return KeepTogether(parts + [table, Spacer(1, 6)])


def side_by_side(left, right, gap=0.3):
    """Place two grids next to each other (each given as a KeepTogether)."""
    return Table([[left._content, right._content]], hAlign="LEFT", style=TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), gap * inch)]))


def band_rows(rows, fmt):
    """Approximate-match bands -> [from, less than, factor] rows."""
    out = []
    for i, (low, value) in enumerate(rows):
        high = f"less than {fmt(rows[i + 1][0])}" if i + 1 < len(rows) else "and over"
        out.append([fmt(low), high, factor(value)])
    return out


def steps(items):
    return [Paragraph(f"{i}.&nbsp;&nbsp;{text}", STEP) for i, text in enumerate(items, 1)]


# ---------------------------------------------------------------- content


def title_page(t):
    big = ParagraphStyle("Big", parent=BODY, fontName="Helvetica-Bold", fontSize=24,
                         leading=30, alignment=TA_CENTER, textColor=INK)
    mid = ParagraphStyle("Mid", parent=BODY, fontSize=14, leading=20, alignment=TA_CENTER)
    box = Table([[Paragraph(
        "<b>FICTIONAL.</b> Example Mutual Insurance Co. does not exist. All names, rates and "
        "rules in this manual were invented for a software demonstration. It is not the "
        "filed manual of any insurer and must not be used to rate real policies.", BODY)]],
        colWidths=[5.6 * inch], hAlign="CENTER")
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.2, INK),
                             ("BACKGROUND", (0, 0), (-1, -1), SHADE),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                             ("TOPPADDING", (0, 0), (-1, -1), 8),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    toc = TableOfContents()
    toc.levelStyles = TOC_LEVELS
    toc.dotsMinLevel = 0
    toc.tableStyle = TableStyle([("TOPPADDING", (0, 0), (-1, -1), 0),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])
    return [
        Spacer(1, 0.5 * inch),
        para(CARRIER, mid),
        Spacer(1, 8),
        para("Homeowners HO-3 Rating Manual", big),
        Spacer(1, 6),
        para(f"Edition {EDITION}", mid),
        Spacer(1, 0.35 * inch),
        box,
        Spacer(1, 0.35 * inch),
        para("<b>Contents</b>", CAPTION),
        toc,
        PageBreak(),
    ]


INPUTS = [
    ("Policy number", "policy_id", "Identifier only; not used in rating"),
    ("Territory", "zone", "Territory code; see R-900"),
    ("Construction class", "construction", "Frame, Masonry, MasonryVeneer or FireResistive"),
    ("Protection class", "protection_class", "Public protection class 1 to 10"),
    ("Year built", "year_built", "Calendar year the dwelling was built"),
    ("Roof age", "roof_age", "Age of the roof covering in whole years"),
    ("Coverage A", "coverage_a", "Dwelling limit in dollars"),
    ("AOP deductible", "deductible", "All-other-perils deductible in dollars; see R-205"),
    ("Hurricane deductible", "hurr_ded_pct", "Percentage of Coverage A; see R-410"),
    ("Central alarm", "alarm", "Alarm indicator; see R-310"),
    ("Wind mitigation", "wind_mit", "None, Basic or Fortified; see R-310 and R-410"),
    ("Claims, prior 3 years", "claims_3yr", "Number of claims; see R-320 and Table 100-F"),
    ("Effective date", "effective_date", "First day of coverage"),
    ("Term", "term_months", "6 or 12 months; see R-420"),
]


def general_section():
    return [
        section_head("Section 1 — General"),
        para("<b>1.1 Purpose.</b> This manual sets out the rules, rates and factors used to "
             f"price a homeowners HO-3 policy written by {CARRIER}. Rules are cited by number, "
             "for example R-205. Rating worksheets and rating systems implement this manual."),
        para("<b>1.2 Scope.</b> The manual covers the dwelling premium for all other perils "
             "(AOP) and for hurricane, credits, term adjustment, the minimum premium, the "
             "policy fee, the assessment and premium tax, and referral to underwriting."),
        grid(["Rating information", "Worksheet field", "Notes"],
             [[a, f"<font name='Courier'>{b}</font>", c] for a, b, c in INPUTS],
             [1.7, 1.55, 3.25], "1.3 Rating information required for each policy"),
        para("<b>1.4 Definitions.</b>"),
        para("<b>Home age</b> is the number of whole years from 1 January of the year built to "
             "the policy effective date. If the year built is later than the effective date, "
             "the home age is 0.", STEP),
        para("<b>Roof age</b> is the reported age of the roof covering in whole years. If no "
             "roof age is reported, the roof is rated as 0 years old.", STEP),
        para("<b>AOP</b> means all perils other than hurricane. <b>Coverage A</b> is the "
             "dwelling limit in dollars. <b>Written premium</b> is the premium after the "
             "minimum premium and the round-up in R-110.", STEP),
        PageBreak(),
    ]


def algorithm_section(t):
    s = t["scalars"]
    items = [
        "<b>Base premium</b> (¢) = AOP base rate for the territory (R-900) × Coverage A / 1,000.",
        "<b>AOP premium</b> (¢) = base premium × construction factor (Table 100-A) × protection "
        "class factor (Table 100-B) × home age factor (Table 100-C) × roof age factor "
        "(Table 100-D) × amount of insurance factor (Table 100-E) × deductible factor (R-205) × "
        "claims factor (Table 100-F).",
        "<b>Credits</b>: net AOP premium (¢) = AOP premium × (1 - total credits), with the "
        "total credits from R-310 and R-320.",
        f"<b>Hurricane</b>: hurricane premium (¢) under R-410, then limited to "
        f"{pct(s['HurrCapPct'])} of Coverage A.",
        "<b>Subtotal</b> = net AOP premium + hurricane premium after the limit.",
        "<b>Term</b>: term premium (¢) = subtotal × term factor (R-420).",
        f"<b>Minimum</b>: the greater of the term premium and the minimum premium of "
        f"{money(s['MinPremium'])} (R-420).",
        "<b>Round up</b>: written premium = the result of step 7 rounded up to the next whole "
        "dollar (R-110).",
        "<b>Fee</b>: policy fee by term (R-510).",
        f"<b>Assessment</b> (¢) = {pct(s['AssessRate'])} × written premium (R-510).",
        "<b>Tax</b>: premium tax (¢) = territory tax rate (R-900) × (written premium + policy "
        "fee) (R-510).",
        "<b>Total due</b> = written premium + policy fee + assessment + premium tax.",
    ]
    return [
        section_head("Section 2 — Rating algorithm"),
        rule_head("R-100", "Rating algorithm"),
        para("Calculate the premium in the following order. Amounts marked (¢) are rounded to "
             "the nearest cent under R-110."),
        *steps(items),
        rule_head("R-110", "Rounding"),
        para("Round to the nearest cent, halves away from zero, after each step in R-100. "
             "Round the final written premium <b>up</b> to the next whole dollar."),
        para("The steps rounded to the cent are those marked (¢) in R-100. The hurricane "
             "limit, the subtotal, the minimum premium comparison and the total due use the "
             "amounts as calculated, with no further rounding. The term factor is rounded to "
             "4 decimal places (R-420)."),
        PageBreak(),
    ]


def factor_tables(t):
    tables = t["tables"]
    constr = tables["RateTables!$A$13:$C$16"]["rows"]
    ppc = tables["RateTables!$A$19:$C$28"]["rows"]
    claims = tables["ClaimsTable"]["rows"]
    top = claims[-1]
    claim_rows = [[f"{int(n)} or more" if n == top[0] else f"{int(n)}", factor(f)]
                  for n, f in claims]
    claim_rows.append(["Not reported (blank)", factor(top[1])])
    return [
        section_head("Section 3 — Rating factors (R-100, step 2)"),
        side_by_side(
            grid(["Construction class", "AOP factor", "Hurricane factor (R-410)"],
                 [[f"<font name='Courier'>{c}</font>", factor(a), factor(h)]
                  for c, a, h in constr],
                 [1.35, 0.75, 1.0], "Table 100-A  Construction"),
            grid(["Protection class", "Frame", "All other construction"],
                 [[int(pc), factor(f), factor(o)] for pc, f, o in ppc],
                 [0.9, 0.7, 1.2], "Table 100-B  Protection class")),
        para("Only the four construction classes in Table 100-A are eligible. In Table 100-B, "
             "every construction class other than Frame uses the right-hand column.", SMALL),
        side_by_side(
            grid(["Home age from (years)", "To", "Factor"],
                 band_rows(tables["AgeBands"]["rows"], num), [1.1, 1.05, 0.7],
                 "Table 100-C  Home age"),
            grid(["Roof age from (years)", "To", "Factor"],
                 band_rows(tables["RoofBands"]["rows"], num), [1.1, 1.05, 0.7],
                 "Table 100-D  Roof age")),
        side_by_side(
            grid(["Coverage A from", "To", "Factor"],
                 band_rows(tables["AOIBands"]["rows"], money), [1.05, 1.45, 0.6],
                 "Table 100-E  Amount of insurance (Coverage A)"),
            grid(["Claims in the prior 3 years", "Factor"], claim_rows, [1.8, 0.6],
                 "Table 100-F  Claims")),
        para("A claims count that is not reported is rated at the factor for "
             f"{int(top[0])} or more claims.", SMALL),
        PageBreak(),
    ]


def deductible_and_credits(t):
    tables = t["tables"]
    cp = dict(zip(tables["CreditPcts"]["header"], tables["CreditPcts"]["rows"][0]))
    cap = t["scalars"]["CreditCap"]
    credits = [
        ["Central alarm", pct(cp["Alarm"]), "The alarm indicator is Y."],
        ["Claims-free", pct(cp["ClaimsFree"]), "See R-320."],
        ["New home", pct(cp["NewHome"]), "Home age is 5 years or less."],
        ["Wind mitigation, basic", pct(cp["MitBasic"]), "Wind mitigation is Basic."],
        ["Wind mitigation, fortified", pct(cp["MitFortified"]), "Wind mitigation is Fortified."],
    ]
    return [
        section_head("Section 4 — Deductibles and credits"),
        rule_head("R-205", "Deductible factors"),
        para("The AOP deductible factor is taken from the band that contains the policy's AOP "
             "deductible. The factor applies to the AOP premium only (R-100, step 2)."),
        grid(["AOP deductible from", "To", "Factor"],
             band_rows(tables["DedBands"]["rows"], money), [1.9, 1.9, 1.2],
             "Table 205  AOP deductible factors"),
        rule_head("R-310", "Premium credits"),
        para("A policy earns each credit below whose condition it meets. Credits are added "
             f"together, and the total credits <b>shall not exceed {pct(cap)}</b>. The net AOP "
             "premium is the AOP premium × (1 - total credits), rounded to the cent. Credits "
             "apply to the AOP premium only, not to the hurricane premium."),
        grid(["Credit", "Percentage", "Condition"], credits, [2.2, 1.1, 3.2],
             "Table 310  Premium credits"),
        para("Any alarm indicator other than Y, including a blank, earns no alarm credit.",
             SMALL),
        rule_head("R-320", "Claims-free credit"),
        para(f"The claims-free credit of {pct(cp['ClaimsFree'])} applies when the number of "
             "claims in the prior 3 years is zero and the home age is at least 3 years. "
             "A blank claims count counts as zero."),
        PageBreak(),
    ]


def hurricane_and_term(t):
    tables = t["tables"]
    s = t["scalars"]
    hd = tables["HurrDedTable"]["rows"]
    wm = tables["RateTables!$K$31:$L$33"]["rows"]
    fees = tables["FeeTable"]["rows"]
    terms = " or ".join(str(int(m)) for m, _ in fees)
    return [
        section_head("Section 5 — Hurricane, term and minimum premium"),
        rule_head("R-410", "Hurricane"),
        para("Hurricane premium (¢) = hurricane base rate for the territory (R-900) × "
             "Coverage A / 1,000 × construction hurricane factor (Table 100-A) × hurricane "
             "deductible factor × wind mitigation factor."),
        para(f"The hurricane premium is capped at <b>{pct(s['HurrCapPct'])} of Coverage A</b>: "
             "the amount used in R-100 is the lesser of the hurricane premium and "
             f"{pct(s['HurrCapPct'])} × Coverage A."),
        para("The hurricane deductible options are " + ", ".join(pct(p) for p, _ in hd[:-1]) +
             f" or {pct(hd[-1][0])} of Coverage A. If no option is chosen, {pct(hd[0][0])} "
             "applies. A percentage that is not one of these options takes factor "
             f"{factor(1)}."),
        side_by_side(
            grid(["Hurricane deductible", "Factor"], [[pct(p), factor(f)] for p, f in hd],
                 [1.7, 0.9], "Table 410-A  Hurricane deductible factors"),
            grid(["Wind mitigation", "Factor"],
                 [[f"<font name='Courier'>{w}</font>", factor(f)] for w, f in wm]
                 + [["Not reported (blank)", factor(1)]],
                 [1.7, 0.9], "Table 410-B  Wind mitigation factors")),
        rule_head("R-420", "Term and minimum premium"),
        para(f"Policies are written for a term of {terms} months. The policy expires on the "
             "same day of the month, 6 or 12 months after the effective date."),
        para("Term factor = the actual number of days from the effective date to the "
             "expiration date / 365, rounded to 4 decimal places. Term premium (¢) = "
             "subtotal × term factor."),
        para(f"The minimum premium of <b>{money(s['MinPremium'])}</b> applies after the term "
             f"factor: the premium is the greater of the term premium and "
             f"{money(s['MinPremium'])}. The result is then rounded up to the next whole "
             "dollar (R-110)."),
        PageBreak(),
    ]


def fees_referral_territories(t):
    tables = t["tables"]
    s = t["scalars"]
    fees = tables["FeeTable"]["rows"]
    zones = tables["BaseRates"]["rows"]
    first, last = zones[0][0], zones[-1][0]
    return [
        section_head("Section 6 — Fees, tax and referral"),
        rule_head("R-510", "Fees and tax"),
        grid(["Term", "Policy fee"], [[f"{int(m)} months", money(f)] for m, f in fees],
             [2.0, 1.4], "Table 510  Policy fee"),
        para(f"Assessment (¢) = {pct(s['AssessRate'])} × written premium."),
        para("Premium tax (¢) = territory tax rate (R-900) × (written premium + policy fee)."),
        para("Total due = written premium + policy fee + assessment + premium tax."),
        para("There are <b>no per-policy overrides</b> of tax: the premium tax is always "
             "calculated by this rule and is never entered or adjusted by hand for an "
             "individual policy."),
        rule_head("R-520", "Referral"),
        para("Refer the policy to underwriting (status REFER) when any of the following "
             "applies; otherwise the status is OK. Referral does not change the premium."),
        *steps(["Coverage A is over $1,000,000.",
                "The roof age is over 20 years.",
                "There are 3 or more claims in the prior 3 years."]),
        para("A claims count that is not reported does not by itself cause a referral.", SMALL),
        PageBreak(),
        section_head("Section 7 — Territories and base rates"),
        rule_head("R-900", "Territories"),
        para(f"Only territories {first} to {last} are eligible. A risk in any other territory "
             "is not eligible and cannot be rated."),
        grid(["Territory", "AOP base rate per $1,000", "Hurricane base rate per $1,000",
              "Premium tax rate"],
             [[z, num(a, 3), num(h, 3), pct(x)] for z, a, h, x in zones],
             [1.1, 1.8, 2.0, 1.4], "Table 900  Base rates and premium tax by territory"),
        para("<b>Appendix A — Statistical fields (informational).</b> These fields are "
             "reported for statistics and do not affect the premium."),
        para("<b>Rate per $1,000</b> = term premium (R-420, before the minimum premium) / "
             "(Coverage A / 1,000), rounded to 3 decimal places.", STEP),
        para("<b>Rate class</b> = the territory code, a hyphen, the first letter of the "
             "construction class, and the protection class as two digits (for example "
             "T03-M05).", STEP),
        para(f"<b>Edition {EDITION}.</b> This edition replaces all earlier editions. {BANNER}.",
             SMALL),
    ]


# ---------------------------------------------------------------- document


class ManualDoc(SimpleDocTemplate):
    """SimpleDocTemplate that registers rule and section headings in the contents."""

    def afterFlowable(self, flowable):
        entry = getattr(flowable, "toc_entry", None)
        if entry:
            self.notify("TOCEntry", (entry[0], entry[1], self.page))


def draw_page(canvas, doc):
    """Running header and the fictional banner footer on every page."""
    canvas.saveState()
    canvas.setDateFormatter(lambda *_: PDF_DATE)
    width, _ = LETTER
    canvas.setFillColor(INK)
    if doc.page > 1:
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.8 * inch, 10.55 * inch,
                          f"{CARRIER} — Homeowners HO-3 Rating Manual")
        canvas.drawRightString(width - 0.8 * inch, 10.55 * inch, f"Edition {EDITION}")
    canvas.setStrokeColor(RULE_GREY)
    canvas.line(0.8 * inch, 0.78 * inch, width - 0.8 * inch, 0.78 * inch)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(0.8 * inch, 0.6 * inch, BANNER)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.8 * inch, 0.45 * inch, f"{CARRIER} · HO-3 Rating Manual · Edition {EDITION}")
    canvas.drawRightString(width - 0.8 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build(tables_path, out_path):
    tables = json.loads(Path(tables_path).read_text(encoding="utf-8"))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = ManualDoc(str(out_path), pagesize=LETTER, invariant=1,
                    leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                    topMargin=0.85 * inch, bottomMargin=0.95 * inch,
                    title=TITLE, author=CARRIER, subject="Synthetic rating manual. " + BANNER,
                    creator="tools/make_manual.py (reportlab)", keywords="FICTIONAL, synthetic")
    story = (title_page(tables) + general_section() + algorithm_section(tables)
             + factor_tables(tables) + deductible_and_credits(tables)
             + hurricane_and_term(tables) + fees_referral_territories(tables))
    doc.multiBuild(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return out_path


def check(out_path):
    """Assert the PDF has 7-10 pages and extractable rule text (needs pypdf)."""
    try:
        from pypdf import PdfReader
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:  # also a broken optional crypto backend (pyo3 panic)
        print(f"check skipped: pypdf unavailable ({type(exc).__name__})", file=sys.stderr)
        return True
    reader = PdfReader(str(out_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    needed = ["R-100", "R-110", "R-205", "R-310", "R-320", "R-410", "R-420", "R-510",
              "R-520", "R-900", "10,000", "FICTIONAL"]
    missing = [s for s in needed if s not in text]
    pages = len(reader.pages)
    ok = 7 <= pages <= 10 and not missing
    print(f"{out_path.name}: {pages} pages, missing text: {missing or 'none'}")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tables", default=str(DEFAULT_TABLES))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-check", action="store_true", help="skip the text/page check")
    args = ap.parse_args(argv)
    out = build(args.tables, args.out)
    if not args.no_check and not check(out):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
