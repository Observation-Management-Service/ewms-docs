#!/bin/bash
set -euo pipefail
#!/usr/bin/env bash

# Write a Sphinx include file that shows a warning banner when a checked-out repo
# is pinned to a specific ref during a manual docs build.

########################################################################
# Validate arguments.
#
# Usage:
#   scripts/write-ref-banner.sh <service-name> <requested-ref> <out-file>
########################################################################

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <service-name> <requested-ref> <out-file>" >&2
    exit 2
else
    service_name="$1"
    requested_ref="$2"
    out_file="$3"
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
# Ensure the output directory exists.
########################################################################

mkdir -p "$(dirname "$out_file")"

########################################################################
# Write the Sphinx include file.
########################################################################

cat > "$out_file" <<EOF
.. raw:: html

   <div class="ewms-ref-banner">
       This page was built from <strong>$service_name ref <code>$requested_ref</code></strong>, not the default branch.
   </div>
EOF
