"""Definitions and figures for the food score pages. Run directly to print them."""
import gzip
import json
import re
import statistics
import sys

GRADES = "ABCDE"
NUTRIENTS = {"energyKcal": "kcal", "sugars": "g", "saturatedFat": "g", "salt": "g", "fiber": "g", "proteins": "g"}

# A product belongs to a group when its name has every word in `all` and none in `none`.
# The lists were set by reading every distinct product name in the group.
GROUPS = {
    "hagelslag": {"all": ["hagelslag"], "none": []},
    "halfvolle-melk": {"all": ["halfvolle", "melk"], "none": ["chocolade", "plantaardig"]},
    "havermout": {"all": ["havermout"], "none": ["reep", "repen", "muesli", "sticks", "granola"]},
    "pindakaas": {"all": ["pindakaas"], "none": []},
    "muesli": {"all": ["muesli"], "none": ["reep", "repen", "biscuits", "yoghurt", "bol"]},
}


def words(name):
    return re.findall(r"[a-zà-ÿ0-9]+", (name or "").lower())


def load(seed):
    with gzip.open(seed, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    seen, graded = set(), []
    for row in rows:
        if row.get("nutriGrade") in tuple("abcde") and row["barcode"] not in seen:
            seen.add(row["barcode"])
            graded.append(row)
    return rows, graded


def members(graded, group):
    out = []
    for row in graded:
        name = words(row["name"])
        if all(w in name for w in group["all"]) and not any(w in name for w in group["none"]):
            out.append(row)
    return out


def figures(products):
    counts = {g: sum(1 for p in products if p["nutriGrade"].upper() == g) for g in GRADES}
    medians = {}
    for key in NUTRIENTS:
        values = [p[key] for p in products if p.get(key) is not None]
        medians[key] = {"value": round(statistics.median(values), 1), "n": len(values)} if len(values) >= 5 else None
    return {"total": len(products), "counts": counts, "medians": medians}


if __name__ == "__main__":
    rows, graded = load(sys.argv[1])
    print("all", len(rows), "graded", len(graded))
    for slug, group in GROUPS.items():
        products = members(graded, group)
        print(slug, json.dumps(figures(products), ensure_ascii=False))
        for label, pattern in {
            "bio/lactose": r"bio|lactose",
            "100": r"100",
            "krokant/crunchy": r"krokant|crunchy|croustillant",
            "geroosterd": r"geroosterd",
            "chocolade": r"choco",
            "smaak/to go/fruit": r"appel|banaan|to go|smaak|blauwe",
            "minder suiker": r"minder suiker",
        }.items():
            hit = [p for p in products if re.search(pattern, p["name"].lower())]
            if hit:
                print("   ", label, len(hit), {g: sum(1 for p in hit if p["nutriGrade"].upper() == g) for g in GRADES})
