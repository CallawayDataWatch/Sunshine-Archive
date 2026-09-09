r"""
csv_to_json.py

Merges a reviewed metadata CSV into docs/data/documents.json, the master
file the website reads.

SAFE TO RE-RUN. This version REPLACES instead of appends: any record
already in documents.json whose 'requester' matches a requester in the
CSV is removed first, then the CSV rows are added fresh. Running it
three times in a row gives the same result as running it once. IDs are
renumbered sequentially every time so there are never duplicates.

Reads the CSV with encoding='utf-8-sig' to strip the invisible BOM that
Excel's "CSV UTF-8" save format adds, which otherwise silently corrupts
the first column.

USAGE:
    python csv_to_json.py <csv_file> <json_file>

EXAMPLE:
    python csv_to_json.py "docs\data\Missouri Protest Organization\mopo_batch.csv" "docs\data\documents.json"
"""

import sys
import os
import csv
import json


def csv_to_records(input_csv):
    """Read every row of the CSV into a list of dicts."""
    with open(input_csv, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            # Strip whitespace from every value, replace None with ''
            clean = {k.strip(): (v or '').strip() for k, v in row.items() if k}
            if not clean.get('filename'):
                continue  # skip blank rows
            records.append(clean)
    return records


def load_existing(json_path):
    """
    Load documents.json. Returns (records_list, wrapper_key).
    wrapper_key is None if the file is a bare list, or the dict key
    if the file is shaped like {"documents": [...]}.
    """
    if not os.path.exists(json_path):
        return [], None
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                return value, key
    raise ValueError(f"Unrecognized structure in {json_path}")


def save(json_path, records, wrapper_key):
    data = records if wrapper_key is None else {wrapper_key: records}
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main(input_csv, json_path):
    new_records = csv_to_records(input_csv)
    if not new_records:
        print("No records found in CSV. Nothing changed.")
        return

    requesters = {r.get('requester', '') for r in new_records if r.get('requester')}
    new_filenames = {r['filename'] for r in new_records}

    existing, wrapper_key = load_existing(json_path)
    before = len(existing)

    # Drop anything already in the JSON that this CSV is replacing:
    # same requester, or same filename.
    kept = [
        rec for rec in existing
        if rec.get('requester', '') not in requesters
        and rec.get('filename', '') not in new_filenames
    ]
    removed = before - len(kept)

    merged = kept + new_records

    # Renumber IDs sequentially so there are never duplicates.
    for i, rec in enumerate(merged, start=1):
        rec['id'] = i

    save(json_path, merged, wrapper_key)

    print(f"Done.")
    print(f"  Removed {removed} old record(s) for: {', '.join(sorted(requesters)) or '(no requester)'}")
    print(f"  Added {len(new_records)} record(s) from {input_csv}")
    print(f"  Total documents in {json_path}: {len(merged)}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python csv_to_json.py <csv_file> <json_file>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
