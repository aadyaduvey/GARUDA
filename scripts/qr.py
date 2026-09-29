"""Make a QR code image for a link:  pnpm qr https://your-site.netlify.app

Saves garuda-qr.png in the project folder (navy on white, high error correction so it
still scans when printed small or slightly damaged).
"""
import sys
from pathlib import Path

import segno

if len(sys.argv) != 2 or not sys.argv[1].startswith("http"):
    sys.exit("Usage: pnpm qr https://your-site.netlify.app")
url = sys.argv[1]
out = Path(__file__).resolve().parent.parent / "garuda-qr.png"
segno.make(url, error="h").save(out, scale=20, border=4, dark="#0d366b")
print(f"QR code for {url} saved to {out}")
