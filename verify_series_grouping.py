import os
import pydicom
from pathlib import Path

# Mocking sanitize_filename from anonimize_gui.py
def sanitize_filename(filename):
    if not filename: return "_invalid_"
    return "".join([c if c.isalnum() or c in (' ', '.', '_', '-') else '_' for c in filename]).strip()

def find_dicom_files(folder):
    dicom_files = []
    for root, _, files in os.walk(folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            if filename.lower().endswith('.dcm'):
                dicom_files.append(file_path)
            else:
                try:
                    with open(file_path, 'rb') as f:
                        f.seek(128)
                        if f.read(4) == b'DICM':
                            dicom_files.append(file_path)
                except: pass
    return dicom_files

def verify_grouping(input_folder, output_log):
    dicom_files = find_dicom_files(input_folder)
    output_log.write(f"Total DICOM files found: {len(dicom_files)}\n")
    
    unique_series = set()
    
    for file_path in dicom_files:
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)
            series_num = ds.get("SeriesNumber", "0")
            series_desc = ds.get("SeriesDescription", "NoDescription")
            series_uid = ds.get("SeriesInstanceUID", "NoUID")
            uid_suffix = series_uid[-5:] if len(series_uid) > 5 else series_uid
            series_folder_name = sanitize_filename(f"{series_num}_{series_desc}_{uid_suffix}")
            
            unique_series.add(series_folder_name)
            
            # Print sample for each NEW unique series found
            if series_folder_name not in [s for s in unique_series if s != series_folder_name]:
                output_log.write(f"Sample File: {os.path.basename(file_path)}\n")
                output_log.write(f"Target Subfolder: {series_folder_name}\n")
                output_log.write("-" * 30 + "\n")
        except Exception as e:
            output_log.write(f"Error reading {file_path}: {e}\n")

    output_log.write(f"\nTotal unique series subfolders that will be created: {len(unique_series)}\n")
    for series in sorted(list(unique_series)):
        output_log.write(f" - {series}\n")

if __name__ == "__main__":
    test_dir = r"C:\Users\jakub\Downloads\FDM_DPI-2024-7-KRN_Prostata_bimodal__MRI_0__Pat11\scans"
    if os.path.isdir(test_dir):
        with open(r"d:\win_app\verify_output.txt", "w", encoding="utf-8") as f:
            verify_grouping(test_dir, f)
        print("Verification complete. Results saved to d:\\win_app\\verify_output.txt")
    else:
        print(f"Test directory not found: {test_dir}")
