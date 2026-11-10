#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${HUMAN_BUILD_CACHE:-/tmp/persona-foundation-build}"
mkdir -p "$CACHE"
fetch() {
  local name="$1" commit="$2"
  if [[ ! -d "$CACHE/$name/.git" ]]; then
    git init "$CACHE/$name"
    git -C "$CACHE/$name" remote add origin "https://github.com/makehumancommunity/$name.git"
  fi
  git -C "$CACHE/$name" fetch --depth 1 origin "$commit"
  git -C "$CACHE/$name" checkout --detach "$commit"
}
fetch mpfb2 6ff1eb358f6c1959ced77e79e6dd2406d9a71f49
fetch makehuman a8bc2d54ff0ac92e78ff71431b1023eda42bf482
export MPFB_SOURCE="$CACHE/mpfb2" MH_SOURCE="$CACHE/makehuman"
export XDG_CONFIG_HOME="$CACHE/config" BLENDER_USER_RESOURCES="$CACHE/blender"
blender -b --python-exit-code 1 --python "$ROOT/tools/build-human.py"
blender -b --python-exit-code 1 --python "$ROOT/tools/portrait-human.py"
blender -b --python-exit-code 1 --python "$ROOT/tools/validate-human.py"

# Verify saved corrective keys and the actual portable skinning, not only topology.
blender -b --python-exit-code 1 --python "$ROOT/tools/validate-poses.py"
blender -b --python-exit-code 1 --python "$ROOT/tools/validate-pose-roundtrip.py"
