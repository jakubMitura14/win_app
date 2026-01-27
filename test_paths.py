import os
import pydicom
from pathlib import Path

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

def test_paths(input_folder, original_output_folder, anonymized_output_folder, generated_id):
    sanitized_id_foldername = sanitize_filename(generated_id)
    dicom_files = find_dicom_files(input_folder)
    
    base_original_path = os.path.join(original_output_folder, sanitized_id_foldername)
    base_anonymized_path = os.path.join(anonymized_output_folder, sanitized_id_foldername)
    
    print(f"Base Original Path: {base_original_path}")
    print(f"Base Anonymized Path: {base_anonymized_path}")
    print(f"Found {len(dicom_files)} DICOM files.\n")
    
    for file_path in dicom_files[:5]: # Just show first 5
        relative_path = os.path.relpath(file_path, input_folder)
        original_output_path = os.path.join(base_original_path, relative_path)
        anonymized_output_path = os.path.join(base_anonymized_path, relative_path)
        
        print(f"Input: {file_path}")
        print(f"Rel:   {relative_path}")
        print(f"Out:   {anonymized_output_path}")
        print("-" * 20)

if __name__ == "__main__":
    input_f = r"C:\Users\jakub\Downloads\FDM_DPI-2024-7-KRN_Prostata_bimodal__MRI_0__Pat11\scans"
    out_orig = r"d:\win_app\test_dicom_out\orig"
    out_anon = r"d:\win_app\test_dicom_out\anon"
    gen_id = "TEST_ID"
    
    test_paths(input_f, out_orig, out_anon, gen_id)
