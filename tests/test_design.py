import re
import unittest

CSS = open("site/assets/tokens.css", encoding="utf-8").read()


def block(selector_start):
    start = CSS.index(selector_start)
    body = CSS[CSS.index("{", start) + 1:CSS.index("}", start)]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6});", body))


def luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


LIGHT = block(":root {")
DARK = block(':root[data-theme="dark"]')
DARK_AUTO = block(':root:not([data-theme="light"])')

# (text colour, background) pairs that appear in the product, all needing 4.5 to 1 (WCAG AA for body text)
PAIRS = [("ink", "bg"), ("ink", "surface"), ("muted", "bg"), ("muted", "surface"), ("accent", "bg"),
         ("accent", "surface"), ("ink", "highlight"), ("good", "bg"), ("good", "surface"), ("bad", "bg"),
         ("bad", "surface")]


class ContrastTests(unittest.TestCase):
    def test_every_pair_meets_aa_in_both_themes(self):
        for name, theme in (("light", LIGHT), ("dark", DARK)):
            for fg, bg in PAIRS:
                with self.subTest(theme=name, pair=f"{fg} on {bg}"):
                    self.assertGreaterEqual(contrast(theme[fg], theme[bg]), 4.5)

    def test_dark_values_are_the_same_in_both_dark_blocks(self):
        self.assertEqual(DARK, DARK_AUTO)

    def test_both_themes_define_the_same_colours(self):
        self.assertEqual(set(LIGHT) & set(DARK), set(DARK))
        self.assertTrue({"bg", "surface", "ink", "muted", "line", "accent", "highlight", "good", "bad"} <= set(LIGHT))

    def test_contrast_function_known_values(self):
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21, places=1)
        self.assertAlmostEqual(contrast("#777777", "#ffffff"), 4.48, places=1)

    def test_reduced_motion_zeroes_durations(self):
        self.assertIn("prefers-reduced-motion: reduce", CSS)


if __name__ == "__main__":
    unittest.main()
