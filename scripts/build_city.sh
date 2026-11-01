#!/bin/sh
# Builds one city's offline files from the Iraq OpenStreetMap extract:
#   <id>-map.pmtiles     vector map (OpenMapTiles schema, same as the app's online style)
#   <id>-routing.tar     Valhalla 3.9 routing graph (must match valhalla-mobile in the app)
#   <id>-search.sqlite   Arabic-aware full-text search index
#
#   scripts/build_city.sh <id> <min_lon,min_lat,max_lon,max_lat> <iraq.osm.pbf> <out-dir>
set -eu

id="$1"; bbox="$2"; iraq="$3"; out="$4"
here=$(cd "$(dirname "$0")" && pwd)
work="$PWD/work"
mkdir -p "$work/$id" "$out"
VALHALLA_IMAGE="${VALHALLA_IMAGE:-ghcr.io/valhalla/valhalla:3.9.0}"
PLANETILER_IMAGE="${PLANETILER_IMAGE:-ghcr.io/onthegomap/planetiler:latest}"

echo "== $id: cut the city out of Iraq"
# "smart" keeps relations (boundaries, multipolygons) whole, which routing's admin data needs.
osmium extract --strategy=smart --bbox "$bbox" "$iraq" -o "$work/$id/city.osm.pbf" --overwrite

echo "== $id: map tiles"
# Planetiler caches its ocean/lake downloads in $work/sources, so only the first city pays for them.
# Default node storage (sorted table, memory-mapped) scales with the extract, not with OSM's largest node
# id; an in-RAM array ran out of heap on the big cities. GitHub's runners have 16 GB.
docker run --rm -e JAVA_TOOL_OPTIONS="-Xmx10g" -v "$work":/data "$PLANETILER_IMAGE" \
  --osm-path="/data/$id/city.osm.pbf" --bounds="$bbox" --download \
  --output="/data/$id/map.pmtiles" --force --maxzoom=14
mv "$work/$id/map.pmtiles" "$out/$id-map.pmtiles"

echo "== $id: routing graph"
docker run --rm --entrypoint /bin/bash -v "$work":/data -w "/data/$id" "$VALHALLA_IMAGE" -c '
  set -e
  mkdir -p tiles
  valhalla_build_config --mjolnir-tile-dir /data/'"$id"'/tiles \
    --mjolnir-tile-extract /data/'"$id"'/routing.tar \
    --mjolnir-timezone /data/timezones.sqlite \
    --mjolnir-admin /data/'"$id"'/admins.sqlite > valhalla.json
  [ -s /data/timezones.sqlite ] || valhalla_build_timezones > /data/timezones.sqlite
  valhalla_build_admins -c valhalla.json city.osm.pbf
  valhalla_build_tiles -c valhalla.json city.osm.pbf
  valhalla_build_extract -c valhalla.json -v --overwrite'
mv "$work/$id/routing.tar" "$out/$id-routing.tar"

echo "== $id: search index"
python3 -X utf8 "$here/build_search_index.py" "$work/$id/city.osm.pbf" "$out/$id-search.sqlite"
# Foursquare Open Source Places, when they were downloaded (needs the HF_TOKEN secret; see fetch_foursquare.py).
if [ -s "$work/fsq-iraq.parquet" ]; then
  (cd "$here" && python3 -X utf8 add_foursquare.py "$out/$id-search.sqlite" "$work/fsq-iraq.parquet" "$bbox")
fi

rm -rf "$work/$id"
ls -lh "$out"/"$id"-*
