#!/usr/bin/env bash
# Generate a PDF of the CV from content/cv.md.
#
# A Python preprocessor converts the HTML tables and blocks in cv.md to raw
# LaTeX fences ({=latex}), then pandoc compiles the result with xelatex.
#
# Usage: ./make_cv_pdf.sh [output_path]
# Default output: static/files/cv_rmanzuk.pdf

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CV_MD="$SCRIPT_DIR/content/cv.md"
PREPROCESS="$SCRIPT_DIR/cv_preprocess.py"
HEADER="$SCRIPT_DIR/cv_latex_header.tex"
OUTPUT="${1:-$SCRIPT_DIR/static/files/cv_rmanzuk.pdf}"

python3 "$PREPROCESS" "$CV_MD" | pandoc \
  --from=markdown \
  --pdf-engine=xelatex \
  -V documentclass=extarticle \
  -V fontsize=10pt \
  -V geometry=margin=1in \
  -V papersize=letter \
  -V colorlinks=true \
  -V urlcolor=MidnightBlue \
  -V linkcolor=Mahogany \
  -H "$HEADER" \
  -o "$OUTPUT"

echo "Generated: $OUTPUT"
