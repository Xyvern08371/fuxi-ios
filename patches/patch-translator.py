#!/usr/bin/env python3
"""Make libmetal2vulkan.dylib carry the AdrenoMetal draw-path patches.

build-fuxi-metal-translator.sh checks the cache out at its pin and refuses a
dirty tree, so a patch in tools/patches never reaches the library that actually
executes the Vulkan calls. This rewrites that script to apply
metal2vulkan-adrenometal-*.patch after the pin check, using a three-way merge
because the patches were authored against a different metal2vulkan revision
(ce5e19e3) than the pinned one (720ef1ce).
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
    '# FUXI_M2V_DRAW_APPLY: 0009-0015 must reach this library; it is the one that\n'
    '# runs the Vulkan calls, and the checkout above resets the cache every build.\n'
    '# The patches were written against ce5e19e3, so a plain apply can reject;\n'
    '# fall back to a three-way merge, then to -C1 context fuzz.\n'
    'draw_patches=$(ls "$(dirname "$0")"/../' + patch_dir + '/metal2vulkan-adrenometal-*.patch 2>/dev/null || true)\n'
    'if [[ -z $draw_patches ]]; then\n'
    '  echo "translator: no adrenometal patches found" >&2\n'
    'else\n'
    '  for p in $draw_patches; do\n'
    '    name=$(basename "$p")\n'
    '    if git -C "$cache" apply --reverse --check "$p" 2>/dev/null; then\n'
    '      echo "translator: already applied $name"\n'
    '    elif git -C "$cache" apply --check "$p" 2>/dev/null; then\n'
    '      git -C "$cache" apply "$p" && echo "translator: applied $name"\n'
    '    elif git -C "$cache" apply -3 --check "$p" 2>/dev/null; then\n'
    '      git -C "$cache" apply -3 "$p" && echo "translator: applied $name (3-way)"\n'
    '    elif git -C "$cache" apply -C1 --check "$p" 2>/dev/null; then\n'
    '      git -C "$cache" apply -C1 "$p" && echo "translator: applied $name (fuzz 1)"\n'
    '    else\n'
    '      echo "translator: REFUSED $name" >&2\n'
    '      exit 1\n'
    '    fi\n'
    '  done\n'
    'fi\n'
)
t = t.replace(anchor, inject, 1)
script.write_text(t)
print('translator: patched to apply AdrenoMetal draw patches (3-way capable)')