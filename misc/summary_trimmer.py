import os
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter

# --- SETTINGS ---
INPUT_FOLDER = "pdfs"                 # Folder containing your PDFs
OUTPUT_FOLDER = "trimmed_pdfs"        # Folder to save trimmed PDFs
HEADER = "CONSTITUENCY DATA - SUMMARY"   # Header text to detect (top only)

# --- CREATE OUTPUT FOLDER IF NOT EXISTS ---
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def trim_pdf(input_path, output_path):
    start_page = None

    # Step 1: Detect header ONLY in top 15% of page
    with pdfplumber.open(input_path) as pdf:
        for i, page in enumerate(pdf.pages):
            w = page.width
            h = page.height

            # crop top 15% of the page
            top_region = page.crop((0, 0, w, h * 0.15))
            txt = top_region.extract_text() or ""

            if HEADER in txt:
                start_page = i
                break

    if start_page is None:
        print(f"[ERROR] Header NOT found in: {input_path}")
        return

    print(f"[OK] Header found on page {start_page + 1} of {input_path}")

    # Step 2: Trim pages using PyPDF2 (no content modification)
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for i in range(start_page, len(reader.pages)):
        writer.add_page(reader.pages[i])

    # Save the trimmed PDF
    with open(output_path, "wb") as f:
        writer.write(f)

    print(f" → Saved trimmed file as: {output_path}\n")


def process_all_pdfs():
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(".pdf")]

    if not files:
        print("No PDF files found in folder:", INPUT_FOLDER)
        return

    print(f"Found {len(files)} PDFs. Starting processing...\n")

    for pdf_file in files:
        input_path = os.path.join(INPUT_FOLDER, pdf_file)
        output_path = os.path.join(
            OUTPUT_FOLDER, pdf_file.replace(".pdf", "_trimmed.pdf")
        )
        trim_pdf(input_path, output_path)

    print("\nAll PDFs processed successfully!")


if __name__ == "__main__":
    process_all_pdfs()
