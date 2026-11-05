#!/usr/bin/env python3
"""Build the checker's public product index from a Basket Vitality product seed.

Usage: build_index.py SEED.jsonl.gz VERSION

Input is the gzipped JSONL the app ships as assets/seed/seed-netherlands.bin.
Use the seed bundled in the live app, so the site and the app agree on scores.

Output is data/products-nl-VERSION.json: one row per product with a Nutri-Score.
The file is a derivative of the Open Food Facts database and is published under
the Open Database License (see data/LICENSE.txt).

Row format: [barcode, name, brand, quantity, grade, flag]
  flag 0: nothing stands out
  flag 1: this database holds no nutrition values for the product (common, and not shown as a warning)
  flag 2: the nutrition values look inconsistent
"""
import gzip
import json
import re
import sys
from pathlib import Path

GRADES = set("abcde")
# Fibre and protein are often absent from labels and records, so they are not required.
CORE_NUTRIENTS = ("energyKcal", "fat", "saturatedFat", "sugars", "salt")


def is_junk_name(name):
    """True for names no shopper could recognise, such as keyboard mashing."""
    if not name or len(name.strip()) < 3:
        return True
    if re.search(r"(.)\1{4,}", name):
        return True
    return not re.search(r"[^\W\d_]{2,}", name)


def quality_flag(row):
    if any(row.get(key) is None for key in CORE_NUTRIENTS):
        return 1
    fat, saturated, kcal = row["fat"], row["saturatedFat"], row["energyKcal"]
    kj = row.get("energyKj")
    if saturated > fat + 0.01:
        return 2
    if fat >= 5 and saturated / fat > 0.8:
        return 2
    if kj is not None and kcal > 0 and not 0.8 < kj / (kcal * 4.184) < 1.2:
        return 2
    if 4 * (row.get("proteins") or 0) + 9 * fat + 2 * (row.get("fiber") or 0) > kcal * 1.35 + 20:
        return 2
    categories = row.get("categoryTags") or ""
    if kcal == 0 and "water" not in categories and "soda" not in categories and "beverage" not in categories:
        return 2
    return 0


def clean(value, limit):
    return re.sub(r"\s+", " ", (value or "")).strip()[:limit]


def build_rows(lines):
    seen = set()
    rows = []
    for line in lines:
        row = json.loads(line)
        if row.get("nutriGrade") not in GRADES or is_junk_name(row.get("name")):
            continue
        barcode = str(row.get("barcode") or "")
        if barcode in seen:
            continue
        seen.add(barcode)
        rows.append([
            barcode,
            clean(row["name"], 90),
            clean(row.get("brands"), 50),
            clean(row.get("quantity"), 24),
            row["nutriGrade"].upper(),
            quality_flag(row),
        ])
    rows.sort(key=lambda r: (r[1].lower(), r[2].lower(), r[0]))
    return rows


def main():
    seed, version = Path(sys.argv[1]), sys.argv[2]
    if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", version):
        sys.exit("VERSION must look like 2026-07 or 2026-07-23")
    with gzip.open(seed, "rt", encoding="utf-8") as handle:
        rows = build_rows(handle)
    out = Path(__file__).resolve().parent.parent / "data" / f"products-nl-{version}.json"
    payload = {
        "version": version,
        "licence": "Open Database License (ODbL) v1.0",
        "attribution": "© Open Food Facts contributors, https://world.openfoodfacts.org",
        "fields": ["barcode", "name", "brand", "quantity", "nutriScore", "qualityFlag"],
        "products": rows,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    counts = [sum(1 for r in rows if r[5] == flag) for flag in (0, 1, 2)]
    print(f"{out.name}: {len(rows)} products, flags {counts}, {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
