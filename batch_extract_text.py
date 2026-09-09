"""
batch_extract_text.py

Extracts text from every PDF in a folder into matching .txt files in
an output folder. Replaces calling pdf2txt.py directly, which on some
Windows setups gets intercepted by the "how do you want to open this
file" dialog instead of running as a command.

USAGE:
    python batch_extract_text.py <pdf_folder> <output_folder>

EXAMPLE:
    python batch_extract_text.py "docs\documents\Missouri Protest Organization" "docs\text\Missouri Protest Organization"
"""

import sys
import os
from pdfminer.high_level import extract_text


def main(pdf_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    pdf_files = sorted(f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf'))

    if not pdf_files:
        print(f"No PDF files found in {pdf_folder}")
        return

    success = 0
    failed = []

    for filename in pdf_files:
        pdf_path = os.path.join(pdf_folder, filename)
        txt_filename = os.path.splitext(filename)[0] + '.txt'
        txt_path = os.path.join(output_folder, txt_filename)

        try:
            text = extract_text(pdf_path)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"OK: {filename} -> {txt_filename} ({len(text)} characters)")
            success += 1
        except Exception as e:
            print(f"FAILED: {filename} -- {e}")
            failed.append(filename)

    print(f"\nDone. {success} of {len(pdf_files)} extracted successfully.")
    if failed:
        print(f"Failed files: {', '.join(failed)}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python batch_extract_text.py <pdf_folder> <output_folder>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
