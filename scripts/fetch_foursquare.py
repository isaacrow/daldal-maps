"""Downloads the open places in Iraq from Foursquare Open Source Places (Apache 2.0) into one Parquet file.

The dataset is on Hugging Face behind a free click-through: HF_TOKEN must be a token of an account that has
accepted the terms at https://huggingface.co/datasets/foursquare/fsq-os-places. Only Iraq's rows and the columns
Daldal uses are read.

    HF_TOKEN=... python3 fetch_foursquare.py work/fsq-iraq.parquet
"""
import json
import os
import sys
import urllib.request

import duckdb


def latest_release(token):
    req = urllib.request.Request("https://huggingface.co/api/datasets/foursquare/fsq-os-places",
                                 headers={"Authorization": f"Bearer {token}"})
    names = [s["rfilename"] for s in json.load(urllib.request.urlopen(req, timeout=60))["siblings"]]
    return sorted({n.split("/")[1] for n in names if n.startswith("release/dt=")})[-1]


def main(out):
    token = os.environ["HF_TOKEN"]
    release = latest_release(token)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"CREATE SECRET hf (TYPE HUGGINGFACE, TOKEN '{token}')")
    con.execute(f"""
        COPY (
            SELECT fsq_place_id, name, latitude, longitude, address, locality, fsq_category_labels
            FROM read_parquet('hf://datasets/foursquare/fsq-os-places/release/{release}/places/parquet/*.parquet')
            WHERE country = 'IQ' AND date_closed IS NULL AND name IS NOT NULL
              AND latitude IS NOT NULL AND longitude IS NOT NULL
        ) TO '{out}' (FORMAT PARQUET)
    """)
    count = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    print(f"Foursquare {release}: {count} open places in Iraq")


if __name__ == "__main__":
    main(sys.argv[1])
