#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Monday 23 November 2026.

Draws a dense dated broadsheet front page (1024x1024 PNG) from 34 real,
sourced news stories of 23 November 2026, grouped by region.

Pure Python 3.13 standard library only: no network, no third-party code,
no embedded images. The picture is drawn pixel by pixel at runtime with
an original 5x7 bitmap font and a hand-written PNG encoder (zlib + struct).

Deterministic: fixed story data, fixed layout, no randomness, no time.
Running twice writes byte-identical files.
"""

import binascii
import os
import struct
import zlib

# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

W, H = 1024, 1024

PAPER = (247, 242, 231)
INK = (22, 22, 22)
SOFT = (88, 84, 76)
RULE = (150, 142, 126)
ACCENT = (148, 32, 20)
BLACKBAR = (24, 24, 24)
WHITE = (250, 248, 242)
CREAMBOX = (238, 231, 214)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.pix = bytearray(w * h * 3)
        self.rect(0, 0, w, h, bg)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pix[i] = color[0]
            self.pix[i + 1] = color[1]
            self.pix[i + 2] = color[2]

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.pix[i] = color[0]
                self.pix[i + 1] = color[1]
                self.pix[i + 2] = color[2]

    def hline(self, x, y, w, color, thick=1):
        self.rect(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.rect(x, y, thick, h, color)


# ---------------------------------------------------------------------------
# 5x7 bitmap font (original glyphs, '#' = ink, '.' = empty)
# ---------------------------------------------------------------------------

FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    'a': ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    'b': ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    'c': ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    'd': ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    'e': ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    'f': ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    'g': ("00000", "01110", "10001", "10001", "01110", "00100", "01110"),
    'h': ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    'i': ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    'j': ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    'k': ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    'l': ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    'n': ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    'o': ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    'p': ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    'q': ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    'r': ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    's': ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    't': ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    'u': ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    'v': ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    'w': ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    'x': ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    'y': ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    'z': ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '*': ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
}

BLANK = ("00000", "00000", "00000", "00000", "00000", "00000", "00000")


def char_advance(scale):
    return 6 * scale


def text_width(text, scale):
    return len(text) * char_advance(scale) - scale


def draw_text(cv, x, y, text, scale, color, bold=False):
    """Draw text with the 5x7 font at integer scale. Returns width used."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, BLANK)
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    for dy in range(scale):
                        for dx in range(scale):
                            cv.set(cx + col * scale + dx, y + row * scale + dy, color)
                            if bold:
                                cv.set(cx + col * scale + dx + 1, y + row * scale + dy, color)
        cx += char_advance(scale)
    return cx - x


def draw_text_centered(cv, cx, y, text, scale, color, bold=False):
    w = text_width(text, scale)
    draw_text(cv, cx - w // 2, y, text, scale, color, bold)


def wrap_text(text, scale, max_width):
    """Greedy word wrap. Returns a list of lines that fit max_width."""
    words = text.split(' ')
    lines = []
    cur = ''
    for word in words:
        trial = word if not cur else cur + ' ' + word
        if text_width(trial, scale) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            # A single over-long word is hard-truncated to fit.
            while text_width(word, scale) > max_width and len(word) > 1:
                word = word[:-1]
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Story data: (region, headline, summary, source)
# Every story was reported on Monday 23 November 2026; source named.
# ---------------------------------------------------------------------------

LEADS = [
    ("CLIMATE", "COP31 ends with no deal",
     "UN climate talks in Turkiye broke down after the EU and others rejected "
     "a final draft that again omitted fossil fuels.",
     "Reuters"),
    ("NORTH AMERICA", "Democrats clinch biggest House majority since 1992",
     "Democrats secured at least 258 seats in the US House, their largest "
     "majority since 1992, final counts showed.",
     "Arab News"),
    ("MIDDLE EAST", "Iran readies tanker convoy to test US blockade",
     "Satellite tracking showed more than 14 Iranian tankers gathering at "
     "Kharg Island to sail through the US naval blockade of the Strait of Hormuz.",
     "Jerusalem Post"),
]

REGIONS = [
    ("ASIA", [
        ("Nepal PM holds talks with Modi in Delhi",
         "Nepal PM Balendra Shah met PM Modi in Delhi to review ties and regional issues.",
         "Observer Voice"),
        ("Seoul education chief quits over AI exam",
         "South Korea's education minister quit in an AI-cheating exam scandal.",
         "Reuters"),
        ("Deadly factory fire in Indonesia",
         "At least three died and dozens were missing after a blaze at a candy factory.",
         "Arab News"),
        ("UN court: Myanmar committed genocide",
         "The ICJ ruled Myanmar committed genocide against the Rohingya Muslim minority.",
         "WH News"),
        ("India piles up record 720 in Wellington",
         "India declared at 720 for 9, a record total, on day four of the Wellington Test.",
         "Observer Voice"),
    ]),
    ("EUROPE", [
        ("Russian ship still burning off Finland",
         "A Russian cargo ship hit in a suspected drone attack kept burning off Finland.",
         "Euronews"),
        ("14 missing after drone strike near Kyiv",
         "At least 14 were missing after a Russian drone hit a home in the Kyiv region.",
         "Jagran Josh"),
        ("Lisbon marches against cost of living",
         "Thousands braved rain in Lisbon to demand higher wages and pensions.",
         "Euronews"),
        ("EU budget keeps 100bn euros for Ukraine",
         "The draft EU budget kept 100 billion euros for Ukraine despite Czech objections.",
         "H.ua"),
        ("Liverpool rout Man Utd 4-0 at Anfield",
         "Liverpool thrashed ten-man Man Utd 4-0 at Anfield in Pochettino's first match.",
         "AP"),
    ]),
    ("NORTH AMERICA", [
        ("Mexico captures FBI most-wanted kingpin",
         "Mexican forces captured 'Chapo Isidro' in Sinaloa; 11 people died in the raid.",
         "CNN"),
        ("FBI probes breach of criminal database",
         "The FBI is probing an apparent breach of its criminal database.",
         "Al Jazeera"),
        ("Governor calls ICE 'out of control'",
         "Washington governor calls ICE 'out of control' after airport arrests.",
         "The True Story"),
        ("Delta delays pile up in Atlanta",
         "An automation glitch caused Delta delays at its Atlanta hub, the airline said.",
         "The True Story"),
        ("US presses Nvidia over China chip sales",
         "The US wants answers from Nvidia about AI chip sales to China, Bessent said.",
         "Arab News"),
        ("Verstappen wins chaotic Las Vegas GP",
         "Verstappen won the Las Vegas GP, a race with 35 lead changes, for a third time.",
         "Virgin Radio Dubai"),
    ]),
    ("SOUTH AMERICA", [
        ("Boca win Copa Sudamericana",
         "Boca won the Copa Sudamericana 2-0; Paredes collapsed in a TV interview after.",
         "EIN News"),
        ("Bolsonaro stable in intensive care",
         "Ex-president Bolsonaro remained stable in intensive care, hospitals said.",
         "UPI"),
        ("Storm kills three in southern Brazil",
         "A supercell storm killed three and damaged thousands of homes in south Brazil.",
         "EIN News"),
        ("CONMEBOL backs Infantino re-election",
         "South America's football body backed Infantino's re-election as FIFA president.",
         "EIN News"),
    ]),
    ("AFRICA", [
        ("Fighting disrupts Congo Ebola response",
         "Fighting near an Ituri hospital forced WHO staff to shelter for over 24 hours.",
         "Reuters"),
        ("24 civilians killed in South Sudan",
         "An SPLA-IO attack left 24 civilians dead in South Sudan, officials said.",
         "Arab News"),
        ("Kenya clears its Ebola cases",
         "Kenya said it had cleared its Ebola cases, with no onward transmission reported.",
         "The Star (Kenya)"),
        ("Uganda tightens borders over Ebola",
         "Uganda restricted border movement and gatherings as the Ebola outbreak went on.",
         "Africa.com"),
    ]),
    ("MIDDLE EAST", [
        ("Two tankers hit in Strait of Hormuz",
         "Two tankers were hit by projectiles in the Strait of Hormuz, the UKMTO reported.",
         "The True Story"),
        ("Saudis intercept Houthi missile",
         "The Saudi-led coalition intercepted a Houthi missile fired at western Saudi.",
         "The Daily Jagran"),
        ("Eisenkot calls settler arson 'terrorism'",
         "Gadi Eisenkot condemned arson attacks on Palestinian homes as 'Jewish terrorism'.",
         "Europe Says"),
        ("Netanyahu-Eisenkot unity talks stall",
         "A second round of Likud-Eisenkot coalition talks ended without agreement.",
         "The True Story"),
    ]),
    ("OCEANIA", [
        ("NZ election too close to call",
         "No clear winner in NZ's election; PM Luxon's coalition holds a razor-thin lead.",
         "WH News"),
        ("Black Foils win SailGP in Dubai",
         "NZ's Black Foils beat Australia to win the Dubai SailGP, their first win of 2026.",
         "Virgin Radio Dubai"),
    ]),
]

NUMBERS = [
    ("258", "Democrats' seats in the US House, biggest majority since 1992"),
    ("100bn", "euros kept for Ukraine in the draft EU budget"),
    ("11,645", "confirmed Ebola cases in DR Congo (WHO, 17 Nov)"),
    ("720", "India's record Test total in Wellington"),
]

DATE_LINE = "23 Nov 2026"
TOTAL_STORIES = 3 + sum(len(s) for _, s in REGIONS)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def story_block_height(headline, summary, width):
    head_lines = wrap_text(headline, 2, width)
    sum_lines = wrap_text(summary, 1, width)
    return len(head_lines) * 15 + 2 + len(sum_lines) * 8 + 2 + 8 + 4


def draw_region_header(cv, x, y, width, name, count):
    cv.rect(x, y, width, 20, BLACKBAR)
    draw_text(cv, x + 8, y + 3, name, 2, WHITE, bold=True)
    tag = "%d stories - %s" % (count, DATE_LINE)
    tw = text_width(tag, 1)
    draw_text(cv, x + width - tw - 8, y + 6, tag, 1, WHITE)


def draw_story(cv, x, y, width, headline, summary, source):
    head_lines = wrap_text(headline, 2, width)
    for line in head_lines:
        draw_text(cv, x, y, line, 2, INK, bold=True)
        y += 15
    y += 2
    sum_lines = wrap_text(summary, 1, width)
    for line in sum_lines:
        draw_text(cv, x, y, line, 1, INK)
        y += 8
    y += 2
    draw_text(cv, x, y, "Source: " + source + "  |  " + DATE_LINE, 1, SOFT)
    y += 8
    return y + 4


# ---------------------------------------------------------------------------
# Page drawing
# ---------------------------------------------------------------------------

def draw_page():
    cv = Canvas(W, H, PAPER)
    mx = 22                      # side margin
    cw = W - 2 * mx              # content width

    # --- outer frame ---
    cv.rect(mx - 6, 14, cw + 12, H - 28, INK)
    cv.rect(mx - 4, 16, cw + 8, H - 32, PAPER)

    # --- masthead ---
    y = 26
    draw_text_centered(cv, W // 2, y, "THE WORLD IN ONE DAY", 6, INK, bold=True)
    y += 44
    cv.hline(mx, y, cw, INK, 3)
    y += 8
    draw_text_centered(cv, W // 2, y, "MONDAY 23 NOVEMBER 2026", 3, ACCENT, bold=True)
    y += 22
    draw_text_centered(
        cv, W // 2, y,
        "%d stories from seven regions - every story sourced, every story dated" % TOTAL_STORIES,
        1, SOFT)
    y += 10
    cv.hline(mx, y, cw, INK, 3)
    y += 10

    # --- lead stories: three columns ---
    lead_top = y
    col_w = (cw - 2 * 16) // 3
    lead_bottom = lead_top
    for i, (region, headline, summary, source) in enumerate(LEADS):
        x = mx + i * (col_w + 16)
        yy = lead_top
        draw_text(cv, x, yy, region, 1, ACCENT, bold=True)
        yy += 11
        cv.hline(x, yy, col_w, RULE, 1)
        yy += 5
        for line in wrap_text(headline, 2, col_w):
            draw_text(cv, x, yy, line, 2, INK, bold=True)
            yy += 15
        yy += 3
        for line in wrap_text(summary, 1, col_w):
            draw_text(cv, x, yy, line, 1, INK)
            yy += 8
        yy += 3
        draw_text(cv, x, yy, "Source: " + source + "  |  " + DATE_LINE, 1, SOFT)
        yy += 9
        lead_bottom = max(lead_bottom, yy)
        if i < 2:
            cv.vline(x + col_w + 8, lead_top, lead_bottom - lead_top, RULE, 1)
    y = lead_bottom + 6
    cv.hline(mx, y, cw, INK, 2)
    y += 6

    # --- by the numbers strip ---
    num_h = 46
    cv.rect(mx, y, cw, num_h, CREAMBOX)
    cv.hline(mx, y, cw, INK, 1)
    cv.hline(mx, y + num_h - 1, cw, INK, 1)
    cell_w = cw // 4
    for i, (num, label) in enumerate(NUMBERS):
        x = mx + i * cell_w
        draw_text(cv, x + 10, y + 7, num, 3, ACCENT, bold=True)
        for j, line in enumerate(wrap_text(label, 1, cell_w - 20)):
            draw_text(cv, x + 10, y + 25 + j * 9, line, 1, INK)
        if i < 3:
            cv.vline(x + cell_w - 1, y + 6, num_h - 12, RULE, 1)
    y += num_h + 6

    # --- region sections in two balanced columns ---
    region_top = y
    gap = 16
    col_w = (cw - gap) // 2
    heights = []
    for name, stories in REGIONS:
        hgt = 20 + 4
        for headline, summary, _src in stories:
            hgt += story_block_height(headline, summary, col_w)
        heights.append(hgt)
    # Greedy balance: assign each region to the shorter column.
    col_a, col_b = [], []
    ha = hb = 0
    for idx, hgt in enumerate(heights):
        if ha <= hb:
            col_a.append(idx)
            ha += hgt
        else:
            col_b.append(idx)
            hb += hgt
    col_x = [mx, mx + col_w + gap]
    col_y = [region_top, region_top]
    for col, idxs in ((0, col_a), (1, col_b)):
        x = col_x[col]
        yy = col_y[col]
        for idx in idxs:
            name, stories = REGIONS[idx]
            draw_region_header(cv, x, yy, col_w, name, len(stories))
            yy += 20 + 4
            for headline, summary, source in stories:
                yy = draw_story(cv, x, yy, col_w, headline, summary, source)
            yy += 2
        col_y[col] = yy
    y = max(col_y) + 2

    # --- footer ---
    cv.hline(mx, y, cw, INK, 2)
    y += 7
    draw_text_centered(
        cv, W // 2, y,
        "All stories reported on Monday 23 November 2026. Sources are named with each story.",
        1, SOFT)
    y += 11
    draw_text_centered(
        cv, W // 2, y,
        "THE WORLD IN ONE DAY  |  %d stories  |  7 regions  |  %s" % (TOTAL_STORIES, DATE_LINE),
        1, SOFT)
    return cv, y + 11


# ---------------------------------------------------------------------------
# PNG encoder (pure stdlib)
# ---------------------------------------------------------------------------

def chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    raw = bytearray()
    row_bytes = cv.w * 3
    for yy in range(cv.h):
        raw.append(0)  # filter: none
        start = yy * row_bytes
        raw += cv.pix[start:start + row_bytes]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    cv, bottom = draw_page()
    size = write_png(path, cv)
    print("wrote %s (%dx%d, %d bytes, %d stories, page bottom y=%d)" % (path, W, H, size, TOTAL_STORIES, bottom))


if __name__ == "__main__":
    main()
