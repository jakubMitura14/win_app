import os
import pydicom
from collections import defaultdict

def sanitize_filename(filename):
    if not filename: return "_invalid_"
    return "".join([c if c.isalnum() or c in (' ', '.', '_', '-') else '_' for c in filename]).strip()

def analyze_series(input_folder):
    series_info = defaultdict(set) # SeriesInstanceUID -> set of (SeriesNumber, SeriesDescription)
    naming_info = defaultdict(set) # (SeriesNumber, SeriesDescription) -> set of SeriesInstanceUIDs
    
    dicom_files = []
    for root, _, files in os.walk(input_folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                with open(file_path, 'rb') as f:
                    f.seek(128)
                    if f.read(4) == b'DICM' or filename.lower().endswith('.dcm'):
                        dicom_files.append(file_path)
            except: pass

    for file_path in dicom_files:
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)
            uid = ds.SeriesInstanceUID
            num = ds.get("SeriesNumber", "0")
            desc = ds.get("SeriesDescription", "NoDescription")
            
            series_info[uid].add((num, desc))
            naming_info[(num, desc)].add(uid)
        except Exception as e:
            pass

    print(f"Total DICOM files: {len(dicom_files)}")
    print(f"Total Unique SeriesInstanceUIDs: {len(series_info)}")
    print(f"Total Unique (Number, Description) pairs: {len(naming_info)}")
    
    collisions = {k: v for k, v in naming_info.items() if len(v) > 1}
    if collisions:
        print("\nCOLLISIONS FOUND (Multiple UIDs for same Number/Description):")
        for (num, desc), uids in collisions.items():
            print(f" - '{num}_{desc}' maps to UIDs:")
            for uid in uids:
                print(f"    - {uid}")
    else:
        print("\nNo collisions found. The current naming logic (Number_Description) is sufficient for this dataset.")

if __name__ == "__main__":
    test_dir = r"C:\Users\jakub\Downloads\FDM_DPI-2024-7-KRN_Prostata_bimodal__MRI_0__Pat11\scans"
    analyze_series(test_dir)
