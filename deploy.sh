#!/bin/bash

# Exit on any error
set -e

echo "▶ Building site with Hugo…"
hugo

echo "✅ Site built into docs/"

echo "▶ Adding changes to git…"
git add .

echo "▶ Committing…"
git commit -m "Build and deploy site on $(date '+%Y-%m-%d %H:%M:%S')"

echo "▶ Pushing to GitHub…"
git push origin main

echo "✅ Done! Site deployed at https://rmanzuk.github.io/"