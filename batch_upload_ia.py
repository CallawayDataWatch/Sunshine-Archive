"""
batch_upload_ia.py

Batch-uploads PDFs to Internet Archive using metadata from your
reviewed CSV, and writes the resulting URL back into the CSV.

IMPORTANT CHANGE FROM EARLIER VERSIONS:
This version checks Internet Archive DIRECTLY to see whether an item
already exists, using the 'ia' command line tool's metadata lookup,
instead of trusting the CSV's 'url' column. This matters because a
CSV can get corrupted or have its url column blanked out by Excel or
by hand-editing, and re-uploading a file that's already on Internet
Archive re-triggers their automatic OCR/derive process, which is what
brought back the ugly Ocr_* metadata box on already-clean items.

With this version, even if the CSV is wrong or empty, the script will
never re-upload something that's genuinely already live on Internet
Archive. It checks the real source of truth every time.

REQUIRES: the 'internetarchive' package installed and configured
    pip install internetarchive
    ia configure

USAGE:
    python batch_upload_ia.py <csv_file> <pdf_folder>

EXAMPLE:
    python batch_upload_ia.py "docs\data\Missouri Protest Organization\mopo_batch.csv" "docs\documents\Missouri Protest Organization"
"""

import sys
import os
import csv
import re
import time
import subprocess

# Seconds to wait between each upload attempt (only applies to files
# that actually need uploading, not ones that are skipped because they
# already exist on Internet Archive).
DELAY_BETWEEN_UPLOADS = 60

# If a rate-limit error is hit, wait this many seconds before retrying
# the same file, doubling each additional retry.
RATE_LIMIT_RETRY_BASE_SECONDS = 60
MAX_RETRIES_PER_FILE = 4


def make_identifier(filename):
    """Build a clean Internet Archive identifier from a filename."""
    base = os.path.splitext(filename)[0]
    base = base.lower()
    base = re.sub(r'[^a-z0-9]+', '-', base)
    base = base.strip('-')
    return base


def item_exists_on_ia(identifier):
    """
    Ask Internet Archive directly whether this item already exists,
    rather than trusting anything in the local CSV. Returns True if
    the item exists and has at least one file uploaded to it.
    """
    result = subprocess.run(
        ['ia', 'metadata', identifier],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False
    # An item with no files yet still returns metadata but with an
    # empty "files" list. A truly nonexistent item returns an error
    # or a response with no 'metadata' key at all. Checking for the
    # 'files' key with actual content is the safest signal.
    return '"files": []' not in result.stdout and '"files":[]' not in result.stdout \
        and '"metadata"' in result.stdout


def upload_one(pdf_path, identifier, row):
    """
    Uses the 'ia' command-line tool to upload one file with metadata.
    Returns (success, error_text).
    """
    title = row.get('title', '').strip() or identifier
    date = row.get('date', '').strip()
    author = row.get('author', '').strip()
    notes = row.get('notes', '').strip()
    requester = row.get('requester', '').strip()
    topic = row.get('topic', '').strip()
    agency = row.get('agency', '').strip()

    description = notes
    if requester:
        description += f" Obtained via Sunshine Request by {requester}."
    description += " Uploaded by Callaway Data Watch as part of a public archive of Sunshine Law requests and responses related to data center development in Missouri."

    subjects = ', '.join(filter(None, [
        'Missouri', 'Sunshine Law', 'public records', 'data center',
        'Callaway Data Watch', 'government transparency', agency, topic
    ]))

    cmd = [
        'ia', 'upload', identifier, pdf_path,
        f'--metadata=title:{title}',
        f'--metadata=description:{description}',
        f'--metadata=mediatype:texts',
        f'--metadata=collection:opensource',
        f'--metadata=subject:{subjects}',
        f'--metadata=language:None',
    ]
    if date:
        cmd.append(f'--metadata=date:{date}')
    if author:
        cmd.append(f'--metadata=creator:{author}')

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, None


def main(csv_path, pdf_folder):
    with open(csv_path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if 'url' not in fieldnames:
        fieldnames = list(fieldnames) + ['url']

    uploaded = 0
    already_live = 0
    failed = []

    for i, row in enumerate(rows, start=1):
        filename = row.get('filename', '').strip()

        if not filename:
            print(f"[{i}] Skipping row with no filename.")
            continue

        identifier = make_identifier(filename)

        print(f"[{i}] Checking Internet Archive for '{identifier}'...")
        if item_exists_on_ia(identifier):
            print(f"  Already live on Internet Archive, skipping upload.")
            row['url'] = f"https://archive.org/details/{identifier}"
            already_live += 1
            continue

        pdf_path = os.path.join(pdf_folder, filename)
        if not os.path.exists(pdf_path):
            print(f"  FAILED: {pdf_path} not found on disk.")
            failed.append(filename)
            continue

        print(f"  Not found on Internet Archive. Uploading...")

        attempt = 0
        success = False
        error_text = None
        while attempt < MAX_RETRIES_PER_FILE:
            success, error_text = upload_one(pdf_path, identifier, row)
            if success:
                break

            is_rate_limit = error_text and 'reduce your request rate' in error_text.lower()
            attempt += 1
            if is_rate_limit and attempt < MAX_RETRIES_PER_FILE:
                wait = RATE_LIMIT_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                print(f"  Rate-limited. Waiting {wait}s before retry {attempt}/{MAX_RETRIES_PER_FILE - 1}...")
                time.sleep(wait)
            elif not is_rate_limit:
                break

        if success:
            row['url'] = f"https://archive.org/details/{identifier}"
            uploaded += 1
            print(f"  OK: {row['url']}")
        else:
            print(f"  FAILED after {attempt} attempt(s): {error_text}")
            failed.append(filename)

        time.sleep(DELAY_BETWEEN_UPLOADS)

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {uploaded} newly uploaded, {already_live} already live on Internet Archive, {len(failed)} failed.")
    if failed:
        print("Failed files (re-run this script to retry just these):")
        for f_name in failed:
            print(f"  - {f_name}")
    print(f"\nUpdated CSV saved: {csv_path}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python batch_upload_ia.py <csv_file> <pdf_folder>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
