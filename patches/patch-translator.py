#!/usr/bin/env python3
"""Make libmetal2vulkan.dylib carry the AdrenoMetal draw-path patches.

build-fuxi-metal-translator.sh runs `git -C $cache checkout --detach $pin` and
then `git -C $cache diff --quiet`, so a patch in tools/patches never reaches the
library that actually executes the Vulkan calls. This rewrites that script to
apply metal2vulkan-adrenometal-*.patch right after the pin check, and to drop
the clean-tree guards that would reject the patched cache.
"""
import sys
from pathlib import Path

script = Path(sys.argv[1])
patch_dir = sys.argv[2] if len(sys.argv) > 2 else 'tools/patches'
t = script.read_text()

if 'FUXI_M2V_DRAW_APPLY' in t:
    print('translator: already patched')
    raise SystemExit(0)

# Drop the clean-tree guards: the patches leave the cache modified by design.
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
    'for p in "$(dirname "$0")"/../' + patch_dir + '/metal2vulkan-adrenometal-*.patch; do\n'
    '  [[ -f $p ]] || continue\n'
    '  if git -C "$cache" apply --reverse --check "$p" 2>/dev/null; then\n'
    '    echo "translator: already applied $(basename "$p")"\n'
    '  elif git -C "$cache" apply --check "$p" 2>/dev/null; then\n'
    '    git -C "$cache" apply "$p"\n'
    '    echo "translator: applied $(basename "$p")"\n'
    '  else\n'
    '    echo "translator: REFUSED $(basename "$p")" >&2\n'
    '    exit 1\n'
    '  fi\n'
    'done\n'
)
t = t.replace(anchor, inject, 1)
script.write_text(t)
print('translator: patched to apply AdrenoMetal draw patches')