import os
import glob
import win32com.client as win32

# --- Configuration ---
# NOTE: Use Windows-style paths (e.g., "D:\\...")
# This script MUST be run on a Windows machine with MS Excel installed.

# Get the current working directory
base_dir = os.getcwd() 

# Define relative paths
input_folder_name = "downloads\\election_data_2014"
output_folder_name = os.path.join(input_folder_name, "converted_xlsx_excel_app")

# Create absolute paths
# os.path.abspath is crucial for the Excel COM object
input_folder = os.path.abspath(os.path.join(base_dir, input_folder_name))
output_folder = os.path.abspath(os.path.join(base_dir, output_folder_name))

# Create the output directory if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

print(f"--- Starting Excel App Conversion ---")
print(f"Input folder: {input_folder}")
print(f"Output folder: {output_folder}")

# Find all .xls files
xls_files = glob.glob(os.path.join(input_folder, "*.xls"))

if not xls_files:
    print(" -> No .xls files found.")
    exit()

# Start the Excel application in the background
try:
    excel = win32.Dispatch('Excel.Application')
    excel.Visible = False
    excel.DisplayAlerts = False # Don't show "do you want to save" popups

    for xls_file_path in xls_files:
        filename = os.path.basename(xls_file_path)
        
        # Define the new .xlsx file path
        xlsx_file_path = os.path.join(output_folder, f"{filename}x")
        
        try:
            print(f"  -> Converting: {filename}")
            # Open the old .xls file
            wb = excel.Workbooks.Open(xls_file_path)
            
            # Save it in the new .xlsx format
            # The FileFormat=51 constant means .xlsx
            wb.SaveAs(xlsx_file_path, FileFormat=51)
            
            wb.Close()
            print(f"  -> Saved: {filename}x")

        except Exception as e:
            print(f"  -> ERROR converting {filename}. Skipping. Reason: {e}")
            # Ensure workbook is closed even on error
            try:
                wb.Close(SaveChanges=False)
            except:
                pass

finally:
    # CRITICAL: Always quit the Excel application
    if 'excel' in locals():
        excel.Quit()
        print("\n--- Excel application closed. Conversion complete! ---")
