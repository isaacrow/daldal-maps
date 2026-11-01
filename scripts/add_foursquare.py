"""Adds Foursquare Open Source Places (Apache 2.0) inside a city's area to its offline search index, so shops,
restaurants, clinics and the like that OpenStreetMap doesn't have yet are found offline too. Places already in the
index (same name within ~80 m) are skipped.

    python3 add_foursquare.py <city>-search.sqlite fsq-iraq.parquet <min_lon,min_lat,max_lon,max_lat>
"""
import sqlite3
import sys

import duckdb

from build_search_index import normalize

# Foursquare category words -> the OpenStreetMap key/value the app understands (PlaceCategory, nearby search).
CATEGORIES = [
    (("restroom", "toilet"), ("amenity", "toilets")),
    (("fast food", "burger", "pizza", "shawarma", "sandwich"), ("amenity", "fast_food")),
    (("restaurant", "diner", "kebab", "grill"), ("amenity", "restaurant")),
    (("café", "cafe", "coffee", "tea room", "juice"), ("amenity", "cafe")),
    (("gas station", "fuel"), ("amenity", "fuel")),
    (("pharmacy", "drugstore"), ("amenity", "pharmacy")),
    (("hospital", "emergency room"), ("amenity", "hospital")),
    (("clinic", "doctor", "dentist", "medical"), ("amenity", "clinic")),
    (("atm",), ("amenity", "atm")),
    (("bank",), ("amenity", "bank")),
    (("mosque", "shrine", "church", "place of worship"), ("amenity", "place_of_worship")),
    (("parking",), ("amenity", "parking")),
    (("hotel", "hostel", "motel", "guest house"), ("tourism", "hotel")),
    (("supermarket", "grocery", "convenience"), ("shop", "supermarket")),
    (("shopping mall", "mall"), ("shop", "mall")),
    (("museum",), ("tourism", "museum")),
    (("park",), ("leisure", "park")),
]


def osm_tag(labels):
    text = " ".join(labels or []).lower()
    for words, tag in CATEGORIES:
        if any(w in text for w in words):
            return tag
    return ("shop", "yes") if "retail" in text else ("fsq", "place")


def main(index, parquet, bbox):
    min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))
    db = sqlite3.connect(index)
    # Existing names on a ~80 m grid, to skip duplicates of OpenStreetMap places.
    seen = set()
    for terms, lat, lon in db.execute("SELECT terms, lat, lon FROM places"):
        seen.add((terms, round(float(lat) * 1200), round(float(lon) * 1200)))
    rows = duckdb.sql(f"""
        SELECT fsq_place_id, name, latitude, longitude, address, locality, fsq_category_labels
        FROM read_parquet('{parquet}')
        WHERE longitude BETWEEN {min_lon} AND {max_lon} AND latitude BETWEEN {min_lat} AND {max_lat}
    """).fetchall()
    added = []
    for fid, name, lat, lon, address, locality, labels in rows:
        terms = normalize(name)
        cell = (round(lat * 1200), round(lon * 1200))
        if any((terms, cell[0] + dy, cell[1] + dx) in seen for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
            continue
        key, value = osm_tag(labels)
        subtitle = "، ".join(x for x in (address, locality) if x)
        added.append((f"fsq:{fid}", name, "", "", subtitle, lat, lon, key, value, terms))
    db.executemany("INSERT INTO places VALUES (?,?,?,?,?,?,?,?,?,?)", added)
    db.execute("INSERT INTO places(places) VALUES('optimize')")
    db.commit()
    db.execute("VACUUM")
    db.close()
    print(f"Foursquare: {len(added)} places added ({len(rows) - len(added)} already in OpenStreetMap)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
