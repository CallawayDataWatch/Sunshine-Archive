"""
parse_metadata.py

Reads OCR-extracted .txt files for a batch of documents and builds a draft
metadata spreadsheet (CSV) that Danielle can review/edit before converting
to documents.json for the Sunshine Archive site.

USAGE:
    python parse_metadata.py <text_folder> <requester_name> <output_csv>

EXAMPLE:
    python parse_metadata.py docs\text\MOPO "Missouri Protest Organization" docs\data\mopo_batch.csv

WHAT IT DOES AUTOMATICALLY:
    - filename       -> pulled from the .txt filename (swapped to .pdf)
    - requester      -> passed in as a command-line argument (folder-based)
    - topic          -> fixed to "Data Center"
    - status         -> fixed to "Received"
    - date           -> regex-scanned from the document text (several common
                        formats). If no date is found, left blank and flagged
                        in a "needs_review" column so it's easy to spot.
    - title / notes  -> draft pulled from the first substantial chunk of
                        extracted text (skips common email header lines like
                        "From:", "To:", "Date:", "Subject:", and boilerplate
                        confidentiality notices). This is a STARTING POINT,
                        meant to be edited, not a final title.

WHAT STILL NEEDS HUMAN REVIEW (left blank or flagged):
    - agency         -> who the request was submitted to / accountable party
    - author         -> who actually wrote/authored the document content
    - title          -> auto-drafted, but should be tightened by hand
    - notes          -> auto-drafted, but should be tightened by hand
    - date           -> auto-detected but ALWAYS spot-check; OCR errors and
                        multiple dates in a document (e.g. forwarded emails)
                        can cause a wrong match

After editing the CSV in Excel/Google Sheets, run csv_to_json.py to build
the final documents.json.
"""

import sys
import os
import re
import csv

# Common date patterns found in emails, letters, and forwarded threads.
DATE_PATTERNS = [
    r'\b(\d{1,2}/\d{1,2}/\d{4})\b',                          # 7/10/2026
    r'\b(\d{4}-\d{2}-\d{2})\b',                              # 2026-07-10
    r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b',  # July 10, 2026
]

# Lines that are just structural noise, skip these when drafting a title/notes.
SKIP_LINE_PREFIXES = (
    'from:', 'to:', 'date:', 'subject:', 're:', 'fw:', 'fwd:',
    'notice:', 'this electronic mail', 'confidential', 'sent:',
    'cc:', 'bcc:',
)


def find_date(text):
    """Return the first date-like string found in the text, or None."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def draft_title_and_notes(text, max_title_words=20, max_notes_chars=400):
    """
    Build a rough title and notes draft from the extracted text.
    Skips header-style lines and boilerplate, grabs the first real
    paragraph of substance instead.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    content_lines = []

    for line in lines:
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in SKIP_LINE_PREFIXES):
            continue
        if len(line) < 15:
            # Too short to be real sentence content (names, single words, etc.)
            continue
        content_lines.append(line)
        if len(content_lines) >= 6:
            break

    if not content_lines:
        return "NEEDS TITLE - no clear text found", "NEEDS REVIEW - could not draft summary"

    combined = ' '.join(content_lines)
    words = combined.split()

    title_draft = ' '.join(words[:max_title_words])
    if len(words) > max_title_words:
        title_draft += '...'

    notes_draft = combined[:max_notes_chars]
    if len(combined) > max_notes_chars:
        notes_draft += '...'

    return title_draft, notes_draft


def process_folder(text_folder, requester, output_csv):
    rows = []
    txt_files = sorted(f for f in os.listdir(text_folder) if f.lower().endswith('.txt'))

    if not txt_files:
        print(f"No .txt files found in {text_folder}. Did you run OCR/text extraction first?")
        return

    for i, txt_filename in enumerate(txt_files, start=1):
        txt_path = os.path.join(text_folder, txt_filename)
        with open(txt_path, encoding='utf-8', errors='replace') as f:
            text = f.read()

        pdf_filename = os.path.splitext(txt_filename)[0] + '.pdf'
        date_found = find_date(text)
        title_draft, notes_draft = draft_title_and_notes(text)

        needs_review = []
        if not date_found:
            needs_review.append('date')
        if title_draft.startswith('NEEDS TITLE'):
            needs_review.append('title/notes')

        rows.append({
            'id': str(i),
            'filename': pdf_filename,
            'url': '',  # fill in after Internet Archive upload
            'title': title_draft,
            'date': date_found or '',
            'agency': '',        # human fills in
            'author': '',        # human fills in
            'requester': requester,
            'request_type': 'Sunshine Request',
            'topic': 'Data Center',
            'status': 'Received',
            'notes': notes_draft,
            'needs_review': ', '.join(needs_review) if needs_review else '',
        })

    fieldnames = ['id', 'filename', 'url', 'title', 'date', 'agency', 'author',
                  'requester', 'request_type', 'topic', 'status', 'notes', 'needs_review']

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    flagged = sum(1 for r in rows if r['needs_review'])
    print(f"Done. Processed {len(rows)} documents.")
    print(f"Output written to: {output_csv}")
    print(f"{flagged} document(s) flagged for review (missing date and/or unclear text).")
    print("Open the CSV in Excel/Google Sheets to review and fill in agency, author, and tighten titles/notes.")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python parse_metadata.py <text_folder> <requester_name> <output_csv>")
        print('Example: python parse_metadata.py docs\\text\\MOPO "Missouri Protest Organization" docs\\data\\mopo_batch.csv')
        sys.exit(1)

    text_folder = sys.argv[1]
    requester = sys.argv[2]
    output_csv = sys.argv[3]

    process_folder(text_folder, requester, output_csv)
