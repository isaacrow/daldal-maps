"""Writes catalog.json: every city with its area and downloadable files (URL, size, SHA-256).

The app downloads https://github.com/<owner>/daldal-maps/releases/latest/download/catalog.json
and offers each city whose three files are present.

    python3 write_catalog.py cities.json <out-dir> <owner/repo> <release-tag>
"""
import hashlib
import json
import os
import sys
import time

cities_path, out, repo, tag = sys.argv[1:5]
cities = json.load(open(cities_path, encoding="utf-8"))
base = f"https://github.com/{repo}/releases/download/{tag}"
KINDS = {"map": "map.pmtiles", "routing": "routing.tar", "search": "search.sqlite"}

catalog = {"version": tag, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cities": []}
for city in cities:
    files = []
    for kind, local_name in KINDS.items():
        asset = f"{city['id']}-{kind}" + os.path.splitext(local_name)[1]
        path = os.path.join(out, asset)
        if not os.path.exists(path):
            break
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
        files.append({"path": local_name, "url": f"{base}/{asset}",
                      "bytes": os.path.getsize(path), "sha256": digest.hexdigest()})
    if len(files) == len(KINDS):
        catalog["cities"].append({**city, "files": files})
    else:
        print(f"skipping {city['id']}: not all files were built", file=sys.stderr)

with open(os.path.join(out, "catalog.json"), "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=1)
total = sum(fl["bytes"] for c in catalog["cities"] for fl in c["files"])
print(f"catalog: {len(catalog['cities'])} cities, {total / 1e6:.0f} MB")
