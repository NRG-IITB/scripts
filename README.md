# Election Data Scripts

This repository contains a collection of Python scripts designed for web-scraping, PDF parsing, and post-processing election data. The toolchain is used to pull election data (typically from PDFs or Excel files), parse the content, normalize entries, and merge them into a standardized format.

## Repository Structure

### Main Pipeline (Root Directory)

These scripts constitute the core workflow for acquiring and processing data.

* **`scrape_xls.py`**: Scrapes election data files (such as Excel or PDF links) from source websites.
* **`parse_data.py`**: The main parsing logic used to extract structured data from raw files (e.g., parsing PDFs and XLS into text/tables).
* **`convert_to_xlsx.py`**: Converts parsed raw data into standardized Excel (`.xlsx`) spreadsheets.
* **`merge_data.py`**: Merges multiple processed datasets into a single master dataset for analysis.

### Utilities (`misc/` Directory)

Helper scripts for data cleaning, validation, and normalization.

* **Data Cleaning:**
    * `party_normalizer.py`: Standardizes political party names to ensure consistency across different years.
    * `summary_trimmer.py`: Removes unnecessary pages (e.g., cover pages) from PDFs.
    * `update_names.py` / `join.py`: Scripts to clean and join GeoJSON or JSON data.
    * `update_xlsx.py`: Edits and standardizes existing Excel sheets.

* **Validation & Metadata:**
    * `check.py` / `match.py`: Checks and matches IDs and Names against a master JSON file to ensure data integrity.
    * `date.py` / `date_fill.py`: Manually adds or fills polling dates into JSON datasets.

## Getting Started

### Prerequisites

You need to install dependencies using:

```bash
pip install pandas openpyxl requests pdfplumber selenium
```

### Usage Workflow

1.  **Scrape Data**: Run `scrape_xls.py` to download the necessary raw files.
2.  **Parse**: Use `parse_data.py` to extract information from the downloaded documents.
3.  **Convert**: Run `convert_to_xlsx.py` to format the parsed data into Excel.
4.  **Clean/Validate**: Use scripts in `misc/` (like `party_normalizer.py` or `check.py`) to clean the data.
5.  **Merge**: Finally, use `merge_data.py` to combine everything into the final dataset.

##  Contributors

* **Ganesha M Mangipudi** (25M0816)
* **Rajat Meher** (25M0777)
* **Niranjan Sharma** (25M0749)