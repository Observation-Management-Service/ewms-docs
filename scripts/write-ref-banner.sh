#!/bin/bash
set -euo pipefail
#!/usr/bin/env bash

# Write a Sphinx include file that shows a warning banner when a checked-out repo
# is pinned to an exact Git tag during a manual docs build.

########################################################################
# Validate arguments.
#
# Usage:
#   scripts/write-ref-banner.sh <repo-dir> <service-name> <requested-ref> <out-file>
########################################################################

if [[ $# -ne 4 ]]; then
    echo "Usage: $0 <repo-dir> <service-name> <requested-ref> <out-file>" >&2
    exit 2
else
    repo_dir="$1"
    service_name="$2"
    requested_ref="$3"
    out_file="$4"
fi

########################################################################
# Validate required inputs.
########################################################################

if [[ -z "$requested_ref" ]]; then
    echo "Error: requested-ref must be non-empty." >&2
    exit 2
else
    :
fi

########################################################################
# Ensure the output directory exists and the output file starts empty.
########################################################################

out_dir="$(dirname "$out_file")"
mkdir -p "$out_dir"
echo -n > "$out_file"

########################################################################
# Detect whether the checked-out commit is exactly a Git tag.
########################################################################

tag="$(git -C "$repo_dir" describe --tags --exact-match 2>/dev/null || true)"

if [[ -z "$tag" ]]; then
    exit 0
else
    :
fi

########################################################################
# Write the Sphinx include file.
########################################################################

cat > "$out_file" <<EOF
.. raw:: html

   <div class="ewms-ref-banner">
       This page was built from <strong>$service_name tag <code>$tag</code></strong>, not the default branch.
   </div>
EOF
