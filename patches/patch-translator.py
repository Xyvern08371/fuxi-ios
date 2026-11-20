#!/usr/bin/env python3
"""Let libmetal2vulkan.dylib carry as many AdrenoMetal draw patches as apply.

build-fuxi-metal-translator.sh checks the cache out at its pin and refuses a
dirty tree, so patches in tools/patches never reached the library that runs the
Vulkan calls. This rewrites the script to try each
metal2vulkan-adrenometal-*.patch after the pin check, in order, with a plain
apply / 3-way merge / fuzz-1 fallback. A patch that cannot apply is reported and
Skipped rather than failing the build: the patches were authored against
ce5e19e3 and the pinned revision is 720ef1ce, so some anchors differ.
"""
import sys
from pathlib import Path

script = Path(sys.argv[1])
patch_dir = sys.argv[2] if len(sys.argv) > 2 else 'tools/patches'
t = script.read_text()

if 'FUXI_M2V_DRAW_APPLY' in t:
    print('translator: already patched')
    raise SystemExit(0)

old_guard = 'git -C "$cache" diff --quiet\ngit -C "$cache" diff --cached --quiet\n'
if old_guard in t:
    t = t.replace(old_guard,
                  '# The AdrenoMetal draw patches below leave this cache modified.\n', 1)

anchor = '[[ $(git -C "$cache" rev-parse HEAD) == "$pin" ]]\n'
if anchor not in t:
    print('translator: pin check not found; not patched')
    raise SystemExit(1)

inject = anchor + (
    '# FUXI_M2V_DRAW_APPLY: as many of 0009-0015 as the pinned revision accepts.\n'
    '# They were authored against ce5e19e3, so a plain apply may reject; try a\n'
    '# three-way merge, then fuzz-1, then report and skip.\n'
    'draw_patches=$(ls "$(dirname "$0")"/../' + patch_dir + '/metal2vulkan-adrenometal-*.patch 2>/dev/null || true)\n'
    'applied=0; skipped=0\n'
    'for p in $draw_patches; do\n'
    '  name=$(basename "$p")\n'
    '  if git -C "$cache" apply --reverse --check "$p" 2>/dev/null; then\n'
    '    echo "translator: already applied $name"; applied=$((applied+1))\n'
    '  elif git -C "$cache" apply --check "$p" 2>/dev/null; then\n'
    '    git -C "$cache" apply "$p" && { echo "translator: applied $name"; applied=$((applied+1)); }\n'
    '  elif git -C "$cache" apply -3 "$p" 2>/dev/null; then\n'
    '    echo "translator: applied $name (3-way)"; applied=$((applied+1))\n'
    '  elif git -C "$cache" apply -C1 "$p" 2>/dev/null; then\n'
    '    echo "translator: applied $name (fuzz 1)"; applied=$((applied+1))\n'
    '  else\n'
    '    echo "translator: SKIPPED $name (does not apply to $pin)"; skipped=$((skipped+1))\n'
    '  fi\n'
    'done\n'
    'echo "translator: draw patches applied=$applied skipped=$skipped"\n'
)
t = t.replace(anchor, inject, 1)
script.write_text(t)
print('translator: patched to apply draw patches non-fatally')