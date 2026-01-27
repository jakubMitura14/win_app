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

def verify_grouping(input_folder):
    dicom_files = find_dicom_files(input_folder)
    print(f"Total DICOM files found: {len(dicom_files)}")
    
    unique_series = set()
    
    for file_path in dicom_files:
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)
            series_num = ds.get("SeriesNumber", "0")
            series_desc = ds.get("SeriesDescription", "NoDescription")
            series_folder_name = sanitize_filename(f"{series_num}_{series_desc}")
            
            unique_series.add(series_folder_name)
            
            # Print first file of each series as a sample
            if series_folder_name not in [s for s in unique_series if s != series_folder_name]:
                print(f"Sample File: {os.path.basename(file_path)}")
                print(f"Target Subfolder: {series_folder_name}")
                print("-" * 30)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    print(f"\nTotal unique series subfolders that will be created: {len(unique_series)}")
    for series in sorted(list(unique_series)):
        print(f" - {series}")

if __name__ == "__main__":
    test_dir = r"C:\Users\jakub\Downloads\FDM_DPI-2024-7-KRN_Prostata_bimodal__MRI_0__Pat11\scans"
    if os.path.isdir(test_dir):
        verify_grouping(test_dir)
    else:
        print(f"Test directory not found: {test_dir}")
