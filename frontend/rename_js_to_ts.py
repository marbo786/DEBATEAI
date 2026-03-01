import os
from pathlib import Path

# Paths to skip
skip_files = {"vite.config.js", "tailwind.config.js", "postcss.config.js"}
frontend_dir = Path("c:/Users/marbo/OneDrive/Desktop/CODING/sem 4/DEBATEAI/frontend")

for p in frontend_dir.rglob("*.jsx"):
    if p.name not in skip_files and "node_modules" not in p.parts:
        p.rename(p.with_suffix(".tsx"))

for p in frontend_dir.rglob("*.js"):
    if p.name not in skip_files and "node_modules" not in p.parts:
        p.rename(p.with_suffix(".ts"))
