import os
import glob
import win32com.client as win32
import shutil # For copying files

# --- Configuration ---
# NOTE: This script MUST be run on a Windows machine with MS Excel installed.

# Get the current working directory
base_dir = os.getcwd() 

# Define the main 'downloads' folder and the new main 'output' folder
main_input_dir = os.path.abspath(os.path.join(base_dir, "downloads"))
main_output_dir = os.path.abspath(os.path.join(base_dir, "converted_xlsx_reports"))

# Create the main output directory if it doesn't exist
os.makedirs(main_output_dir, exist_ok=True)

print(f"--- Starting Enhanced Excel App Conversion ---")
print(f"Scanning for 'election_data_*' folders in: {main_input_dir}")
print(f"Output will be saved to: {main_output_dir}")

# Find all 'election_data_*' folders
year_folders = glob.glob(os.path.join(main_input_dir, "election_data_*"))

if not year_folders:
    print(" -> No 'election_data_*' folders found.")
    exit()

# Start the Excel application in the background
excel = None
try:
    excel = win32.Dispatch('Excel.Application')
    excel.Visible = False
    excel.DisplayAlerts = False # Don't show "do you want to save" popups

    # Loop over each year's folder
    for input_folder in year_folders:
        folder_name = os.path.basename(input_folder)
        print(f"\nProcessing folder: {folder_name}")

        # Define the corresponding output folder for this year
        # e.g., "converted_xlsx_reports/election_data_2019_xlsx"
        output_folder_name = f"{folder_name}_xlsx"
        output_folder = os.path.join(main_output_dir, output_folder_name)
        os.makedirs(output_folder, exist_ok=True)
        print(f"  -> Outputting to: {output_folder_name}")

        # Find all .xls and .xlsx files in the current input folder
        files_to_process = glob.glob(os.path.join(input_folder, "*.xls*"))

        if not files_to_process:
            print("  -> No .xls or .xlsx files found in this folder.")
            continue # Move to the next year folder

        for file_path in files_to_process:
            filename = os.path.basename(file_path)
            name_without_ext, extension = os.path.splitext(filename)
            
            if extension.lower() == '.xls':
                # --- This is an .xls file, CONVERT IT ---
                new_filename = f"{name_without_ext}.xlsx"
                xlsx_file_path = os.path.join(output_folder, new_filename)
                
                try:
                    print(f"  -> Converting: {filename}")
                    # Open the old .xls file
                    wb = excel.Workbooks.Open(file_path)
                    
                    # Save it in the new .xlsx format (FileFormat=51)
                    wb.SaveAs(xlsx_file_path, FileFormat=51)
                    
                    wb.Close(SaveChanges=False) # Close original without saving
                    print(f"  -> Saved: {new_filename}")

                except Exception as e:
                    print(f"  -> ERROR converting {filename}. Skipping. Reason: {e}")
                    # Ensure workbook is closed even on error
                    try:
                        if 'wb' in locals():
                            wb.Close(SaveChanges=False)
                    except:
                        pass # wb might not be defined or already closed

            elif extension.lower() == '.xlsx':
                # --- This is already an .xlsx file, COPY IT ---
                destination_path = os.path.join(output_folder, filename)
                try:
                    print(f"  -> Copying (already .xlsx): {filename}")
                    shutil.copy2(file_path, destination_path) # copy2 preserves metadata
                except Exception as e:
                    print(f"  -> ERROR copying {filename}. Skipping. Reason: {e}")

            else:
                # Skip other files like .crdownload or .pdf
                print(f"  -> Skipping file (not .xls or .xlsx): {filename}")


finally:
    # CRITICAL: Always quit the Excel application
    if excel:
        excel.Quit()
        print("\n--- Excel application closed. All folders processed. ---")
    else:
        print("\n--- Processing complete (Excel app was not started). ---")

