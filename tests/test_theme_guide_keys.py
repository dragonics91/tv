"""themes/CREATE_A_THEME.md's examples name only keys the launcher reads, and the guide is reachable.

A theme's `config.json` is an overlay on `config.xml` and the launcher ignores a key it does not know, so a
key that is not in the Keys table here changes nothing on the TV and says nothing about it. That is fine for
a theme that carries one (themes/retro/README.md explains its `dock_band` as a switch from a launcher build
of its own), but the guide a new author follows is the one place an example key is taken as authority: its
time-of-day block listed `"dock_band": false` among sixteen keys the launcher does read, and no key of that
name has ever been a launcher setting - `dock_band` was a colour resource, renamed before it could be a key -
so an author copying the block got a config.json where one line did nothing, and the guide's own note ("an
unknown key is ignored") is what kept them from finding out. The block no longer carries it.

Second half, same page: nothing linked it. `themes/README.md` is the page a theme author opens, its "Adding a
theme" section is the checklist they follow, and it sent a reader to a new folder and a row without naming
the guide that walks the same job from the TV side - `grep -rn CREATE_A_THEME` over the repository found the
page's own title and nothing else, so it was only reachable by a folder listing. The section links it now,
and the link test below keeps every page in `themes/` reachable from that README.

The keys are not copied into this file: they come from the Keys table in themes/README.md, which
tests/test_theme_keys_config.py already holds to every key the launcher reads from config.xml, so a key the
table stops carrying, or a launcher that starts reading one the table never gained, moves this test with it.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEMES = ROOT / "themes"
README = THEMES / "README.md"
GUIDE = THEMES / "CREATE_A_THEME.md"

# A row of the Keys table: | `key` | type | what it does |, the shape tests/test_theme_keys_config.py reads.
TABLE_ROW = re.compile(r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|", re.M)
# A fenced block, with the language it declares. A theme's config.json is the only JSON in the guide.
FENCE = re.compile(r"^```([a-zA-Z0-9]*)[ \t]*\n(.*?)^```", re.S | re.M)
# A markdown link or image destination, the form tests/test_markdown_links.py reads.
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def table_keys(page):
    """Every key the Keys table lists in one page, in file order."""
    return set(TABLE_ROW.findall(page))


def json_blocks(page):
    """(index, text) for every fenced block the page declares as JSON."""
    return [(i, body) for i, (lang, body) in enumerate(FENCE.findall(page)) if lang.lower() == "json"]


def example_keys(page):
    """{key: block number} for the top-level keys of each of the page's JSON blocks.

    Only the object's own keys count: a key inside a value (`wallpaper_moods`' `morning`) is data for that
    key, not a setting of its own, and reporting it would make this test refuse a correct example.
    """
    out = {}
    for number, (_, body) in enumerate(json_blocks(page)):
        try:
            parsed = json.loads(body)
        except ValueError as e:
            raise AssertionError(f"a JSON block in the page does not parse: {e}") from e
        if not isinstance(parsed, dict):
            raise AssertionError(f"a JSON block in the page is a {type(parsed).__name__}, not an object")
        for key in parsed:
            out.setdefault(key, number)
    return out


def unknown_keys(page, known):
    """Keys in the page's examples that the Keys table does not carry, in file order."""
    return {key: block for key, block in example_keys(page).items() if key not in known}


def linked_pages(page):
    """The relative .md pages one page links, as resolved paths."""
    out = set()
    for target in LINK.findall(page):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        local = target.split("#")[0]
        if local.endswith(".md"):
            out.add(local)
    return out


def guide_pages(folder):
    """Every .md page sitting in a theme folder's top level, README.md aside."""
    return sorted(p.name for p in folder.glob("*.md") if p.name != "README.md")


class ThemeGuideKeysTest(unittest.TestCase):
    def setUp(self):
        self.page = GUIDE.read_text(encoding="utf-8")
        self.known = table_keys(README.read_text(encoding="utf-8"))

    def test_the_keys_table_was_read(self):
        # The Keys table is the source of truth here; a page this test could not read would make every
        # assertion below pass by finding nothing.
        self.assertGreaterEqual(len(self.known), 50,
                                f"the Keys table in themes/README.md lists {len(self.known)} keys, so this "
                                "test is reading the wrong table")

    def test_every_example_key_is_a_key_the_launcher_reads(self):
        blocks = json_blocks(self.page)
        self.assertGreaterEqual(len(blocks), 2,
                                "the guide should keep at least its time-of-day and its single-picture "
                                f"example, found {len(blocks)} JSON block(s)")
        found = example_keys(self.page)
        self.assertGreaterEqual(len(found), 10,
                                f"read {len(found)} keys out of the guide's examples, which is too few for a "
                                "config.json - the block format changed and this test is no longer reading it")
        unknown = unknown_keys(self.page, self.known)
        message = "\n".join(
            f"themes/CREATE_A_THEME.md block {number}: '{key}' is not in the Keys table of themes/README.md, "
            f"so a theme carrying it changes nothing on the TV"
            for key, number in unknown.items())
        self.assertEqual({}, unknown, message)

    def test_the_readme_links_every_theme_page(self):
        pages = guide_pages(THEMES)
        self.assertIn("CREATE_A_THEME.md", pages,
                      "the guide is the page this test exists for; if it moved, point this test at its new home")
        linked = linked_pages(README.read_text(encoding="utf-8"))
        missing = [name for name in pages if name not in linked]
        self.assertEqual([], missing,
                         "pages in themes/ that themes/README.md does not link: " + ", ".join(missing))

    def test_a_linked_page_resolves(self):
        for target in linked_pages(self.page):
            self.assertTrue((GUIDE.parent / target).exists(),
                            f"themes/CREATE_A_THEME.md links {target}, which is not there")


class ThemeGuideReaderTest(unittest.TestCase):
    """The readers above, on pages written here, so a reader that stops reading fails instead of passing."""

    def test_an_unknown_key_is_reported_with_its_block(self):
        page = ('# Guide\n\n```json\n{"background_color": "#000000"}\n```\n\n'
                '```json\n{"glass_style": "rim", "dock_band": false}\n```\n')
        self.assertEqual({"dock_band": 1}, unknown_keys(page, {"background_color", "glass_style"}))

    def test_known_keys_are_quiet(self):
        page = '```json\n{"columns": 5, "wallpaper": true}\n```\n'
        self.assertEqual({}, unknown_keys(page, {"columns", "wallpaper"}))

    def test_a_page_with_no_json_block_has_no_keys(self):
        page = "See `config.json` in [themes/retro/](retro/) for an example.\n"
        self.assertEqual({}, example_keys(page))

    def test_a_block_that_is_not_json_is_not_read(self):
        page = '```bash\ntools/theme.sh themes/aurora\n```\n'
        self.assertEqual([], json_blocks(page))

    def test_a_key_inside_a_value_is_not_a_key_of_its_own(self):
        page = '```json\n{"wallpaper_moods": {"morning": ["a.jpg"]}}\n```\n'
        keys = example_keys(page)
        self.assertIn("wallpaper_moods", keys)
        self.assertNotIn("morning", keys)

    def test_a_page_that_cannot_be_read_is_not_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "themes"
            folder.mkdir()
            (folder / "README.md").write_text("| `columns` | int | layout |\n", encoding="utf-8")
            (folder / "CREATE_A_THEME.md").write_text("```json\n{\"dock_band\": false}\n```\n",
                                                     encoding="utf-8")
            known = table_keys((folder / "README.md").read_text(encoding="utf-8"))
            page = (folder / "CREATE_A_THEME.md").read_text(encoding="utf-8")
            self.assertEqual({"dock_band": 0}, unknown_keys(page, known))

    def test_the_link_reader_reads_relative_pages_only(self):
        page = ("[a](CREATE_A_THEME.md) [b](https://example.com/x.md) [c](retro/screenshot.jpg) "
                "[d](README.md#keys) [e](#adding-a-theme)\n")
        # A link may carry an anchor of its own; the page is still the target, as tests/test_markdown_links.py reads it.
        self.assertEqual({"CREATE_A_THEME.md", "README.md"}, linked_pages(page))

    def test_a_theme_page_nothing_links_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "themes"
            folder.mkdir()
            (folder / "README.md").write_text("# Themes\n", encoding="utf-8")
            (folder / "OLD_GUIDE.md").write_text("# Old\n", encoding="utf-8")
            pages = guide_pages(folder)
            linked = linked_pages((folder / "README.md").read_text(encoding="utf-8"))
            self.assertEqual(["OLD_GUIDE.md"], [name for name in pages if name not in linked])


if __name__ == "__main__":
    unittest.main()
