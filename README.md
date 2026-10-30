# Daldal city maps

Offline maps, routing graphs and search indexes for Iraqi cities, used by the Daldal app.
Built weekly by GitHub Actions from OpenStreetMap; each release holds, per city:

| File | What it is |
|---|---|
| `<city>-map.pmtiles` | Vector map tiles (OpenMapTiles schema), built with Planetiler |
| `<city>-routing.tar` | Valhalla 3.9 routing graph |
| `<city>-search.sqlite` | Full-text search index with Arabic normalization |
| `catalog.json` | Every city's area, files, sizes and SHA-256 checksums |

Cities and their areas are listed in [`cities.json`](cities.json) (centres from Wikidata, CC0).

To rebuild one city by hand: **Actions › Build city maps › Run workflow**, and enter its id (e.g. `zakho`).

## Licence

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the
[Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). These files are a derived
database and are published under the same licence. The build scripts are MIT-licensed.
