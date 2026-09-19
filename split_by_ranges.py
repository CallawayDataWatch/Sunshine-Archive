"""
split_by_ranges.py

Splits one large multi-document PDF into individual PDFs, one per document,
based on a page list you provide.

STEP 1: Create a plain text file (e.g. ranges.txt) with one line per
document. Two formats are supported, and you can mix both in the same file:

  SEQUENTIAL RANGE (most documents):
      start-end   (1-indexed physical page numbers in the big PDF, inclusive)

      Example: "5-7" means this document is physical pages 5, 6, and 7,
      in that order.

  OUT-OF-ORDER PAGE LIST (for documents where the physical pages are
  scanned out of sequence, but still identifiable by their printed page
  numbers or content):
      page,page,page   (comma-separated, in the CORRECT reading order)

      Example: "14,12,13" means this document should be assembled by
      taking physical page 14 first, then physical page 12, then
      physical page 13 -- i.e. the pages were scanned out of order and
      this puts them back in the right sequence.

  A single-page document can be written either as "4-4" or just "4".

EXAMPLE ranges.txt:
    1-1
    2-1
    3-2
    14,12,13
    5-3

STEP 2: Run this script:
    python split_by_ranges.py <big_pdf> <ranges_file> <output_folder> <prefix>

EXAMPLE:
    python split_by_ranges.py "docs\\originals\\Missouri Protest Organization\\MOPO Sunshine Request 2026.pdf" ranges.txt "docs\\documents\\Missouri Protest Organization" mopo

This creates mopo-001.pdf, mopo-002.pdf, etc. in the output folder,
one file per line in ranges.txt, in the order given in that file.
"""

import sys
from pypdf import PdfReader, PdfWriter


def parse_ranges(ranges_file):
    """
    Returns a list of page-lists. Each entry is a list of 1-indexed
    physical page numbers, in the order they should appear in the
    output document.
    """
    entries = []
    with open(ranges_file, encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            if ',' in line:
                # Out-of-order explicit page list, e.g. "14,12,13"
                try:
                    pages = [int(p.strip()) for p in line.split(',')]
                except ValueError:
                    print(f"Line {line_num} ('{line}') has non-numeric values, skipping.")
                    continue
                entries.append(pages)

            elif '-' in line:
                # Sequential range, e.g. "5-7"
                start_str, end_str = line.split('-', 1)
                try:
                    start, end = int(start_str), int(end_str)
                except ValueError:
                    print(f"Line {line_num} ('{line}') has non-numeric values, skipping.")
                    continue
                if start > end:
                    print(f"Line {line_num} ('{line}') has start > end, skipping.")
                    continue
                entries.append(list(range(start, end + 1)))

            else:
                # Single page number, e.g. "4"
                try:
                    page = int(line)
                except ValueError:
                    print(f"Line {line_num} ('{line}') isn't recognized, skipping.")
                    continue
                entries.append([page])

    return entries


def split_pdf(big_pdf_path, entries, output_folder, prefix):
    reader = PdfReader(big_pdf_path)
    total_pages = len(reader.pages)

    for i, pages in enumerate(entries, start=1):
        if any(p < 1 or p > total_pages for p in pages):
            print(f"Skipping document {i}: pages {pages} include an out-of-bounds "
                  f"page number (PDF only has {total_pages} pages).")
            continue

        writer = PdfWriter()
        for page_num in pages:
            writer.add_page(reader.pages[page_num - 1])

        out_filename = f"{prefix}-{i:03}.pdf"
        out_path = f"{output_folder}\\{out_filename}"
        with open(out_path, 'wb') as f:
            writer.write(f)

        page_desc = ','.join(str(p) for p in pages)
        print(f"Document {i}: physical page(s) {page_desc} -> {out_filename}")

    print(f"\nDone. {len(entries)} document(s) written to {output_folder}")


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: python split_by_ranges.py <big_pdf> <ranges_file> <output_folder> <prefix>")
        print(r'Example: python split_by_ranges.py "docs\originals\Missouri Protest Organization\MOPO Sunshine Request 2026.pdf" ranges.txt "docs\documents\Missouri Protest Organization" mopo')
        sys.exit(1)

    big_pdf, ranges_file, output_folder, prefix = sys.argv[1:5]
    entries = parse_ranges(ranges_file)
    split_pdf(big_pdf, entries, output_folder, prefix)
