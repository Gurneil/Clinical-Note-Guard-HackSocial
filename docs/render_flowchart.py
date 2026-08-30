"""
Renders docs/workflow_flowchart.html to docs/workflow_flowchart.png - the
workflow diagram used in the project documentation and submission.

The diagram is authored as HTML/CSS and rendered by whichever Chromium-based
browser is already installed, at 2x device scale so the small print (the
verbatim QUERY lines, which show exactly what is asked of each model)
stays crisp at 100% zoom. It replaced a matplotlib
script whose every box coordinate was hand-derived: text there could not
wrap or reflow, so any edit to a node's wording meant re-tuning the geometry
of every box below it.

Dev-time tool, not part of the runtime pipeline. Needs Pillow for the
whitespace trim; the browser is whatever the OS already has.

    python docs/render_flowchart.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(HERE, "workflow_flowchart.html")
OUT_PATH = os.path.join(HERE, "workflow_flowchart.png")

# Rendered viewport, in CSS pixels. WIDTH must match the body width in the
# HTML plus nothing - the body sets its own width, so this only needs to be
# >= it. HEIGHT is deliberately generous; the surplus is trimmed below,
# which is cheaper than a second headless pass just to measure the document.
WIDTH = 1250
HEIGHT = 5200
SCALE = 2

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    for path in CANDIDATES:
        if os.path.exists(path):
            return path
    for name in ("chrome", "chromium", "msedge", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit("No Chromium-based browser found; edit CANDIDATES in this script.")


def trim(path):
    """Crop the unused tail of the fixed-height viewport.

    Trims against the corner pixel rather than a hardcoded background colour,
    so re-theming the page does not silently turn this into a no-op.
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        print("Pillow not installed - leaving the render untrimmed.")
        return
    with Image.open(path) as im:
        im = im.convert("RGB")
        bg = Image.new("RGB", im.size, im.getpixel((0, 0)))
        bbox = ImageChops.difference(im, bg).getbbox()
        if not bbox:
            return
        pad = 30 * SCALE
        left, upper, right, lower = bbox
        cropped = im.crop((
            max(0, left - pad),
            max(0, upper - pad),
            min(im.width, right + pad),
            min(im.height, lower + pad),
        ))
        cropped.save(path)
        print(f"Trimmed to {cropped.width}x{cropped.height}")


def main():
    browser = find_browser()
    # Chrome writes the screenshot relative to its own cwd and needs a
    # writable profile dir; give it a scratch one so a running Chrome
    # instance's profile lock doesn't make this fail intermittently.
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-color-profile=srgb",
                f"--user-data-dir={profile}",
                f"--window-size={WIDTH},{HEIGHT}",
                f"--force-device-scale-factor={SCALE}",
                f"--screenshot={OUT_PATH}",
                "file:///" + HTML_PATH.replace("\\", "/"),
            ],
            check=True,
        )
    trim(OUT_PATH)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
