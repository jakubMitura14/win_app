import flet as ft
import os
import pydicom
import shutil
import csv
from pathlib import Path
import concurrent.futures
import re
import threading
import traceback  # For detailed error logging

# --- Constants ---
PREFIX = "FDM_DPI-2024-7-KRN"
PROJECTS = {
    "Lu177_PSMA": f"{PREFIX}^Lu177_PSMA",
    "Prostata_bimodal": f"{PREFIX}^Prostata_bimodal",
    "SD": f"{PREFIX}^SD",
}
METADATA_HEADER = ["PatientID", "FirstName", "LastName", "StudyDate", "ProjectID", "Modality", "PatientNumberStr"]

# --- Helper Functions ---

def sanitize_filename(filename):
    """Removes or replaces characters invalid for filenames/foldernames."""
    if not isinstance(filename, str):  # Handle potential non-string input
        return "_invalid_"
    sanitized = re.sub(r'[<>:"/\\|?*^]', '_', filename)
    sanitized = sanitized.replace("||", "__")
    sanitized = sanitized.rstrip('. ')
    max_len = 100
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "_truncated"
    return sanitized if sanitized else "_invalid_"

def get_project_metadata_path(metadata_folder, project_id):
    """Constructs the path to the project-specific metadata CSV file. Returns None on error."""
    if not metadata_folder or not project_id:
        print("Warning: Cannot get metadata path, missing folder or project ID.")
        return None
    if not os.path.isdir(metadata_folder):
        print(f"Warning: Metadata folder '{metadata_folder}' is not a valid directory.")
        return None
    safe_project_id = sanitize_filename(project_id)
    if not safe_project_id or safe_project_id == "_invalid_":
        print(f"Warning: Invalid project ID '{project_id}' for metadata filename.")
        return None
    filename = f"{safe_project_id}_metadata.csv"
    return os.path.join(metadata_folder, filename)

def find_next_patient_number(metadata_folder, project_id):
    """
    Reads the project-specific CSV and suggests the next patient number (e.g., 'PatX').
    Returns 'Pat1' if file doesn't exist, has no relevant entries, or on error.
    """
    metadata_file_path = get_project_metadata_path(metadata_folder, project_id)
    if not metadata_file_path:
        return "Pat1"

    max_num = 0
    file_exists = os.path.isfile(metadata_file_path)

    if file_exists:
        try:
            with open(metadata_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                first_char = csvfile.read(1)
                if not first_char:
                    return "Pat1"
                csvfile.seek(0)

                reader = csv.DictReader(csvfile)
                if "PatientNumberStr" not in reader.fieldnames:
                    print(f"Warning: 'PatientNumberStr' column missing in {metadata_file_path}. Defaulting to Pat1.")
                    return "Pat1"

                for row in reader:
                    pat_str = row.get("PatientNumberStr", "").strip()
                    match = re.match(r"Pat(\d+)", pat_str, re.IGNORECASE)
                    if match:
                        try:
                            num = int(match.group(1))
                            if num > max_num:
                                max_num = num
                        except ValueError:
                            print(f"Warning: Could not parse number in PatientNumberStr '{pat_str}' in {metadata_file_path}")
                            continue
            return f"Pat{max_num + 1}"
        except FileNotFoundError:
            return "Pat1"
        except Exception as e:
            print(f"Error reading metadata file '{metadata_file_path}' to find next patient number: {e}")
            traceback.print_exc()
            return "Pat1"
    else:
        return "Pat1"

def find_next_study_number(metadata_folder, project_id, patient_number_str):
    """
    Returns the next study number for a given patient in a project.
    Study number is incremented for each entry with the same patient_number_str,
    regardless of modality or other fields.
    """
    metadata_file_path = get_project_metadata_path(metadata_folder, project_id)
    if not metadata_file_path or not patient_number_str:
        return 1

    max_study = 0
    file_exists = os.path.isfile(metadata_file_path)
    if file_exists:
        with open(metadata_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            first_char = csvfile.read(1)
            if not first_char:
                return 1
            csvfile.seek(0)
            reader = csv.DictReader(csvfile)
            # Accept both with and without StudyNumber in header
            for row in reader:
                if row.get("PatientNumberStr", "").strip() == patient_number_str:
                    try:
                        # If StudyNumber column exists, use it, else count rows
                        if "StudyNumber" in reader.fieldnames:
                            snum = int(row.get("StudyNumber", "0"))
                            if snum > max_study:
                                max_study = snum
                        else:
                            max_study += 1
                    except Exception:
                        continue
    return max_study + 1

def search_patients_by_surname(metadata_folder, project_id, surname_query):
    """
    Searches the project-specific CSV for patients matching the surname query.
    If surname_query is empty, returns all unique patients for the project.
    Returns a list of dictionaries, each containing 'display', 'first_name', 'last_name', 'patient_number_str'.
    Returns empty list on error or if no matches found.
    """
    results = []
    metadata_file_path = get_project_metadata_path(metadata_folder, project_id)
    if not metadata_file_path:
         print(f"Warning: Cannot search, invalid metadata path for project '{project_id}'.")
         return results

    if not os.path.isfile(metadata_file_path):
        print(f"Info: Metadata file not found for search: {metadata_file_path}")
        return results

    try:
        with open(metadata_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            first_char = csvfile.read(1)
            if not first_char:
                return results
            csvfile.seek(0)

            reader = csv.DictReader(csvfile)
            required_cols = ["FirstName", "LastName", "PatientNumberStr"]
            if not all(col in reader.fieldnames for col in required_cols):
                print(f"Warning: Missing required columns (FirstName, LastName, PatientNumberStr) for search in {metadata_file_path}.")
                return results

            processed_patients = set()
            surname_query_lower = surname_query.lower() # Prepare for comparison

            for row in reader:
                last_name = row.get("LastName", "").strip()
                pat_num_str = row.get("PatientNumberStr", "").strip()

                if pat_num_str and pat_num_str not in processed_patients:
                    if not surname_query or surname_query_lower in last_name.lower():
                        first_name = row.get("FirstName", "").strip()
                        results.append({
                            "display": f"{first_name} {last_name} ({pat_num_str})",
                            "first_name": first_name,
                            "last_name": last_name,
                            "patient_number_str": pat_num_str
                        })
                        processed_patients.add(pat_num_str)

            results.sort(key=lambda x: x["display"])
        return results
    except Exception as e:
        print(f"Error searching patients in '{metadata_file_path}': {e}")
        traceback.print_exc()
        return []

def find_dicom_files(folder):
    """
    Recursively finds all valid DICOM files in a folder.
    Checks for '.dcm' extension or reads the header for magic number 'DICM'.
    """
    dicom_files = []
    if not os.path.isdir(folder):
        print(f"Error: Input folder '{folder}' not found or is not a directory.")
        return dicom_files

    for root, _, files in os.walk(folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            is_dicom = False
            # Check 1: File extension (optional but fast)
            if filename.lower().endswith('.dcm'):
                is_dicom = True
            # Check 2: Read magic number 'DICM' at byte 128 if extension doesn't match or doesn't exist
            if not is_dicom:
                try:
                    with open(file_path, 'rb') as f:
                        f.seek(128)
                        magic = f.read(4)
                        if magic == b'DICM':
                            is_dicom = True
                except Exception:
                    # Ignore files that can't be read or are too small
                    pass
            # Check 3: Try parsing with pydicom as a final confirmation (more robust but slower)
            if is_dicom:
                 try:
                     # Attempt to read metadata to ensure it's parseable DICOM
                     pydicom.dcmread(file_path, stop_before_pixels=True)
                     dicom_files.append(file_path)
                 except pydicom.errors.InvalidDicomError:
                     print(f"Warning: File '{file_path}' looked like DICOM but failed to parse.")
                 except Exception as e:
                     print(f"Warning: Error reading file '{file_path}': {e}")

    return dicom_files

def copy_non_anonymized_dicom(input_path, output_path, status_callback=None):
    """Copies a file using shutil.copy2 to preserve metadata."""
    try:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        error_msg = f"ERROR copying original file '{os.path.basename(input_path)}': {e}"
        if status_callback: status_callback(error_msg)
        print(error_msg)
        traceback.print_exc()
        return False

def anonymize_dicom_file(input_path, output_path, chosen_id, status_callback=None):
    """Anonymizes a DICOM file by changing PatientID and clearing other tags."""
    try:
        ds = pydicom.dcmread(input_path)

        # --- Tags to Anonymize/Clear ---
        # Modify PatientID
        ds.PatientID = chosen_id

        # Clear other potentially identifying information
        tags_to_clear = [
            "PatientName", "PatientBirthDate", "PatientSex", "PatientAge",
            "PatientAddress", "PatientTelephoneNumbers", "ReferringPhysicianName",
            "InstitutionName", "InstitutionAddress", "OperatorsName",
            "OtherPatientIDs", "OtherPatientNames", "PatientComments",
            "RequestingPhysician", "PerformingPhysicianName",
            # Add any other tags you need to clear
        ]

        for tag_name in tags_to_clear:
            if tag_name in ds:
                # Get the VR (Value Representation) to clear appropriately
                vr = ds[tag_name].VR
                if vr in ('SH', 'LO', 'ST', 'LT', 'UT', 'PN'): # String types
                    ds[tag_name].value = ""
                elif vr in ('DA', 'DT', 'TM'): # Date/Time types
                    ds[tag_name].value = "" # Or a fixed dummy date/time if required
                elif vr == 'UI': # UID - replace with dummy or leave if needed for structure
                     ds[tag_name].value = "" # Clearing might be simpler if allowed
                elif vr == 'AS': # Age String
                     ds[tag_name].value = ""
                # Add handling for other VRs if necessary

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the modified dataset
        ds.save_as(output_path)

        return True

    except pydicom.errors.InvalidDicomError:
        error_msg = f"ERROR: File '{os.path.basename(input_path)}' is not a valid DICOM file."
        if status_callback: status_callback(error_msg)
        print(error_msg)
        return False
    except Exception as e:
        error_msg = f"ERROR anonymizing file '{os.path.basename(input_path)}': {e}"
        if status_callback: status_callback(error_msg)
        print(error_msg)
        traceback.print_exc()
        return False

def process_single_file(file_path, input_folder_base, metadata, base_original_path, base_anonymized_path, status_callback=None):
    """
    Processes a single DICOM file: copies original and creates anonymized version.
    Returns (success_copy, success_anon, study_date).
    """
    success_copy = False
    success_anon = False
    study_date = None
    generated_id = metadata.get("generated_id", "UNKNOWN_ID") # Get chosen ID

    try:
        # Calculate relative path to maintain structure
        relative_path = os.path.relpath(file_path, input_folder_base)

        # Construct full output paths
        original_output_path = os.path.join(base_original_path, relative_path)
        anonymized_output_path = os.path.join(base_anonymized_path, relative_path)

        # Ensure output directories exist for the specific file
        os.makedirs(os.path.dirname(original_output_path), exist_ok=True)
        os.makedirs(os.path.dirname(anonymized_output_path), exist_ok=True)

        # 1. Copy the original file
        success_copy = copy_non_anonymized_dicom(file_path, original_output_path, status_callback)

        # 2. Anonymize the file
        success_anon = anonymize_dicom_file(file_path, anonymized_output_path, generated_id, status_callback)

        # 3. Extract StudyDate (do this once, e.g., from the original read for anonymization)
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)
            study_date = ds.get("StudyDate", None) # Get StudyDate if it exists
        except Exception as date_e:
             if status_callback: status_callback(f"  Warning: Could not read StudyDate from {os.path.basename(file_path)}: {date_e}")


    except Exception as e:
        error_msg = f"ERROR processing file '{os.path.basename(file_path)}' in main loop: {e}"
        if status_callback: status_callback(error_msg)
        print(error_msg)
        traceback.print_exc()
        success_copy = False
        success_anon = False

    return success_copy, success_anon, study_date

def save_metadata_to_table(metadata_dict, metadata_folder, status_callback=None):
    """Appends patient metadata to the project-specific CSV file."""
    project_id = metadata_dict.get("project_id")
    metadata_file_path = get_project_metadata_path(metadata_folder, project_id)

    if not metadata_file_path:
        if status_callback: status_callback("ERROR: Could not determine metadata file path.")
        return False

    file_exists = os.path.isfile(metadata_file_path)
    is_empty = (not file_exists) or (os.path.getsize(metadata_file_path) == 0)

    try:
        os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)

        # --- Add StudyNumber to header if not present ---
        header = METADATA_HEADER.copy()
        if "StudyNumber" not in header:
            header.insert(header.index("PatientNumberStr") + 1, "StudyNumber")

        with open(metadata_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header)

            if is_empty:
                writer.writeheader()

            row_data = {field: metadata_dict.get(field.lower().replace("patientnumberstr", "patient_number_str"), "") for field in header}
            row_data["PatientID"] = metadata_dict.get("generated_id", "")
            row_data["FirstName"] = metadata_dict.get("first_name", "")
            row_data["LastName"] = metadata_dict.get("last_name", "")
            row_data["StudyDate"] = metadata_dict.get("study_date", "")
            row_data["ProjectID"] = metadata_dict.get("project_id", "")
            row_data["Modality"] = metadata_dict.get("modality", "")
            row_data["PatientNumberStr"] = metadata_dict.get("patient_number_str", "")
            row_data["StudyNumber"] = metadata_dict.get("study_number", "")

            writer.writerow(row_data)
            if status_callback:
                status_callback(f"Metadata saved to {os.path.basename(metadata_file_path)}")
            return True
    except Exception as e:
        if status_callback:
            status_callback(f"ERROR saving metadata: {e}")
        print(f"Error writing to metadata file '{metadata_file_path}': {e}")
        traceback.print_exc()
        return False

def process_patient_study(metadata, status_callback=None, progress_callback=None):
    """
    Processes all DICOM files for a patient study based on collected metadata.
    Handles copying originals and anonymizing files. Saves to project-specific metadata.
    Includes progress reporting via progress_callback.
    """
    input_folder = metadata.get("input_folder")
    original_output_folder = metadata.get("original_output_folder")
    anonymized_output_folder = metadata.get("anonymized_output_folder")
    metadata_folder = metadata.get("metadata_folder")
    generated_id = metadata.get("generated_id")
    project_id = metadata.get("project_id")

    required_fields = ["input_folder", "original_output_folder", "anonymized_output_folder", "metadata_folder",
                       "generated_id", "project_id", "patient_number_str", "first_name", "last_name"]
    missing = [k for k in required_fields if not metadata.get(k)]
    if missing:
        if status_callback: status_callback(f"ERROR: Missing required metadata fields: {', '.join(missing)}")
        return False

    if not os.path.isdir(input_folder):
        if status_callback: status_callback(f"ERROR: Input path '{input_folder}' is not a valid directory.")
        return False
    if not os.path.isdir(metadata_folder):
        if status_callback: status_callback(f"ERROR: Metadata folder path '{metadata_folder}' is not a valid directory.")
        return False

    sanitized_id_foldername = sanitize_filename(generated_id)
    if not sanitized_id_foldername or sanitized_id_foldername == "_invalid_":
        if status_callback: status_callback(f"ERROR: Could not create a valid folder name from generated ID '{generated_id}'.")
        return False

    if status_callback: status_callback("Scanning for DICOM files...")
    dicom_files = find_dicom_files(input_folder)
    total_files = len(dicom_files)

    if not dicom_files:
        if status_callback: status_callback("No valid DICOM files found in the input folder.")
        return False
    else:
        if status_callback: status_callback(f"Found {len(dicom_files)} DICOM files. Starting processing...")

    base_original_path = os.path.join(original_output_folder, sanitized_id_foldername)
    base_anonymized_path = os.path.join(anonymized_output_folder, sanitized_id_foldername)

    try:
        os.makedirs(base_original_path, exist_ok=True)
        os.makedirs(base_anonymized_path, exist_ok=True)
    except Exception as e:
        if status_callback: status_callback(f"ERROR: Could not create base output directories: {e}")
        print(f"Error creating base output directories: {e}")
        traceback.print_exc()
        return False

    copy_count = 0
    anonymized_count = 0
    first_study_date = None

    if progress_callback: progress_callback(0.0)

    for i, file_path in enumerate(dicom_files):
        try:
            success_copy, success_anon, study_date = process_single_file(
                file_path,
                input_folder,
                metadata,
                base_original_path,
                base_anonymized_path,
                status_callback
            )
            if success_copy: copy_count += 1
            if success_anon: anonymized_count += 1
            if study_date and first_study_date is None:
                first_study_date = study_date
        except Exception as file_proc_e:
            error_msg = f"CRITICAL ERROR processing file {os.path.basename(file_path)}: {file_proc_e}"
            if status_callback: status_callback(error_msg)
            print(error_msg)
            traceback.print_exc()

        if progress_callback: progress_callback((i + 1) / total_files)

    if progress_callback: progress_callback(1.0)

    metadata["study_date"] = first_study_date if first_study_date else "Unknown"

    if status_callback: status_callback("Saving metadata...")
    save_success = save_metadata_to_table(metadata, metadata_folder, status_callback)

    metadata_file_path = get_project_metadata_path(metadata_folder, project_id)
    metadata_loc_str = os.path.basename(metadata_file_path) if metadata_file_path else "N/A"
    summary = (
        f"Processing complete. \n"
        f"  Input files found: {len(dicom_files)}\n"
        f"  Originals copied: {copy_count}\n"
        f"  Files anonymized: {anonymized_count}\n"
        f"  Metadata saved: {'Yes' if save_success else 'No'} (to {metadata_loc_str})\n"
        f"  Output (Originals): {base_original_path}\n"
        f"  Output (Anonymized): {base_anonymized_path}\n"
        f"  Metadata Folder: {metadata_folder}"
    )
    if status_callback:
        status_callback(summary)
    else:
        print(summary)

    return anonymized_count == len(dicom_files) and copy_count == len(dicom_files)

class DicomAnonymizerApp:
    def __init__(self):
        self.page = None
        self.search_results_data = []
        self.patient_number_suggestion_lock = threading.Lock()
        self.search_lock = threading.Lock()

        self.input_folder_path = ft.Text("No input folder selected")
        self.original_output_folder_path = ft.Text("No original output folder selected")
        self.anonymized_output_folder_path = ft.Text("No anonymized output folder selected")
        self.metadata_folder_path = ft.Text("No metadata folder selected")

        self.input_picker = ft.FilePicker(on_result=self.on_folder_result)
        self.original_output_picker = ft.FilePicker(on_result=self.on_folder_result)
        self.anonymized_output_picker = ft.FilePicker(on_result=self.on_folder_result)
        self.metadata_picker = ft.FilePicker(on_result=self.on_folder_result)

        self.first_name_field = ft.TextField(label="Patient First Name", on_change=self.validate_inputs, expand=True)
        self.last_name_field = ft.TextField(label="Patient Last Name", on_change=self.validate_inputs, expand=True)
        self.patient_number_field = ft.TextField(label="Patient Number", tooltip="Format: Pat followed by digits (e.g., Pat123)", on_change=self._handle_input_change, expand=1)

        self.modality_radio_group = ft.RadioGroup(content=ft.Row([
                ft.Radio(value="MRI", label="MRI"),
                ft.Radio(value="CT", label="CT"),
                ft.Radio(value="PETPSMA", label="PET PSMA"),
                ft.Radio(value="PETFDG", label="FDG PET"),
                ft.Radio(value="SPECT_Iodine", label="SPECT_Iodine"),
                ft.Radio(value="SPECT_Tc", label="SPECT_Tc"),
                ft.Radio(value="SPECT_MIBI", label="SPECT_MIBI"),
                ft.Radio(value="Scintigraphy_Tc", label="Scintigraphy_Tc"),
                ft.Radio(value="Scintigraphy_Iodine", label="Scintigraphy_Iodine"),
                ft.Radio(value="Other", label="Other"),
            ]), on_change=self._handle_input_change)
        self.other_modality_field = ft.TextField(label="Other Modality", visible=False, on_change=self._handle_input_change)

        project_dropdown_options = [
            ft.dropdown.Option(key=proj_id, text=f"{proj_id}")
            for proj_id in PROJECTS.keys()
        ]
        project_dropdown_options.append(ft.dropdown.Option(key="Other", text="Other"))
        self.project_dropdown = ft.Dropdown(
            label="Project",
            options=project_dropdown_options,
            on_change=self._handle_input_change,
            tooltip="Select the project for this study"
        )
        self.custom_project_field = ft.TextField(label="Custom Project ID", visible=False, on_change=self._handle_input_change)

        self.study_number_field = ft.TextField(
            label="Study Number", value="1",
            input_filter=ft.InputFilter(allow=True, regex_string=r"[1-9][0-9]*", replacement_string=""),
            on_change=self._handle_input_change, width=150
        )

        self.generated_id_field = ft.TextField(label="Generated Patient ID", read_only=False, on_change=self.validate_inputs, tooltip="Auto-generated, but can be manually edited")

        self.surname_search_field = ft.TextField(label="Search Existing Patient by Surname", on_change=self.on_surname_search_change, expand=True)
        self.search_results_dropdown = ft.Dropdown(label="Select Existing Patient", options=[], on_change=self.on_search_result_select, visible=False, expand=2)

        self.status_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        self.start_button = ft.ElevatedButton(
            text="Start Processing",
            on_click=self.start_processing,
            disabled=True,
            icon=ft.icons.PLAY_ARROW_ROUNDED
        )
        self.progress_ring = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)
        self.progress_bar = ft.ProgressBar(visible=False, width=400)

    def pick_folder(self, e, picker_ref: ft.FilePicker, title: str):
        """Opens the directory picker associated with the button."""
        picker_ref.get_directory_path(dialog_title=title)

    def _update_patient_number_suggestion(self):
        """Suggests the next patient number based on current project and metadata folder."""
        threading.Thread(target=self._fetch_and_set_suggestion, daemon=True).start()

    def _fetch_and_set_suggestion(self):
        """Worker function to get suggestion and update UI."""
        if not self.patient_number_suggestion_lock.acquire(blocking=False):
            print("Suggestion fetch already in progress.")
            return

        try:
            metadata_folder = self.metadata_folder_path.value
            project_id = self.project_dropdown.value
            if project_id == "Other":
                project_id = self.custom_project_field.value.strip()

            suggested_pat_num = "Pat1"
            if os.path.isdir(metadata_folder) and project_id:
                suggested_pat_num = find_next_patient_number(metadata_folder, project_id)

            if self.page:
                if not self.patient_number_field.value:
                    self.patient_number_field.value = suggested_pat_num
                    self.update_generated_id()
                    self.validate_inputs()
                    self.page.update()
        except Exception as e:
            print(f"Error during patient number suggestion fetch: {e}")
            traceback.print_exc()
        finally:
            self.patient_number_suggestion_lock.release()

    def _handle_input_change(self, e):
        """Handles changes in relevant fields to update UI state and generated ID."""
        control = e.control
        project_or_metadata_changed = control == self.project_dropdown or \
                                      control == self.custom_project_field or \
                                      control == self.metadata_folder_path

        self.other_modality_field.visible = (self.modality_radio_group.value == "Other")
        self.custom_project_field.visible = (self.project_dropdown.value == "Other")

        if project_or_metadata_changed:
            if control == self.project_dropdown or control == self.custom_project_field:
                self.first_name_field.value = ""
                self.last_name_field.value = ""
                self.patient_number_field.value = ""
                self.surname_search_field.value = ""
                self.search_results_dropdown.options = []
                self.search_results_dropdown.value = None
                self.search_results_dropdown.visible = False

            self._update_patient_number_suggestion()

        # Suggest next study number when patient number changes or project changes
        if e.control == self.patient_number_field or e.control == self.project_dropdown or e.control == self.custom_project_field:
            metadata_folder = self.metadata_folder_path.value
            project_id = self.project_dropdown.value
            if project_id == "Other":
                project_id = self.custom_project_field.value.strip()
            patient_number_str = self.patient_number_field.value.strip()
            if os.path.isdir(metadata_folder) and project_id and patient_number_str:
                next_study = find_next_study_number(metadata_folder, project_id, patient_number_str)
                self.study_number_field.value = str(next_study)

        self.update_generated_id()
        self.validate_inputs()
        if self.page: self.page.update()

    def on_surname_search_change(self, e):
        """Callback when surname search text changes. Triggers search."""
        surname_query = self.surname_search_field.value.strip()
        metadata_folder = self.metadata_folder_path.value
        project_id = self.project_dropdown.value
        if project_id == "Other":
            project_id = self.custom_project_field.value.strip()

        self.search_results_dropdown.options = []
        self.search_results_dropdown.value = None
        self.search_results_dropdown.visible = False
        self.search_results_data = []

        if os.path.isdir(metadata_folder) and project_id:
            if self.search_lock.acquire(blocking=False):
                threading.Thread(target=self._perform_search, args=(metadata_folder, project_id, surname_query), daemon=True).start()
            else:
                print("Search already in progress...")
        else:
            if self.page: self.page.update()

    def _perform_search(self, metadata_folder, project_id, surname_query):
        """Performs the actual search and updates the dropdown (intended for background thread)."""
        try:
            search_term_log = f"'{surname_query}'" if surname_query else "(all patients)"
            print(f"Searching for {search_term_log} in project '{project_id}'...")
            self.search_results_data = search_patients_by_surname(metadata_folder, project_id, surname_query)
            options = [ft.dropdown.Option(key=i, text=result["display"]) for i, result in enumerate(self.search_results_data)]
            print(f"Found {len(options)} results.")

            if self.page:
                self.search_results_dropdown.options = options
                self.search_results_dropdown.value = None
                self.search_results_dropdown.visible = bool(options)
                self.page.update()
        except Exception as e:
            print(f"Error during search execution: {e}")
            traceback.print_exc()
        finally:
            self.search_lock.release()

    def on_search_result_select(self, e):
        """Callback when a patient is selected from the search results dropdown."""
        try:
            selected_index_str = self.search_results_dropdown.value
            if selected_index_str is not None:
                selected_index = int(selected_index_str)
                if 0 <= selected_index < len(self.search_results_data):
                    selected_patient = self.search_results_data[selected_index]
                    self.first_name_field.value = selected_patient["first_name"]
                    self.last_name_field.value = selected_patient["last_name"]
                    self.patient_number_field.value = selected_patient["patient_number_str"]
                    # Suggest next study number for this patient
                    metadata_folder = self.metadata_folder_path.value
                    project_id = self.project_dropdown.value
                    if project_id == "Other":
                        project_id = self.custom_project_field.value.strip()
                    patient_number_str = selected_patient["patient_number_str"]
                    if os.path.isdir(metadata_folder) and project_id and patient_number_str:
                        next_study = find_next_study_number(metadata_folder, project_id, patient_number_str)
                        self.study_number_field.value = str(next_study)
                    self.update_generated_id()
                    self.validate_inputs()
                    if self.page: self.page.update()
        except (ValueError, IndexError) as ex:
            print(f"Error handling search result selection: {ex}")

    def update_generated_id(self):
        """Constructs the Patient ID based on current selections including patient number and study number."""
        try:
            project_id = self.project_dropdown.value
            if project_id == "Other":
                project_id = self.custom_project_field.value.strip()
            elif project_id is None: project_id = ""

            modality = self.modality_radio_group.value
            if modality == "Other":
                modality = self.other_modality_field.value.strip().upper()
                if not modality: modality = "OTHER"
            elif modality is None:
                modality = ""

            study_number_str = self.study_number_field.value.strip()
            if not study_number_str or not study_number_str.isdigit() or int(study_number_str) < 1:
                study_number = 1
            else:
                study_number = int(study_number_str)
            study_index = study_number - 1

            patient_part = self.patient_number_field.value.strip()
            is_valid_pat_format = bool(patient_part) and re.match(r"Pat\d+", patient_part, re.IGNORECASE) is not None

            if not project_id or not modality or not is_valid_pat_format:
                self.generated_id_field.value = ""
                self.generated_id_field.error_text = "Invalid format or missing info" if (project_id and modality and patient_part and not is_valid_pat_format) else None
                return

            self.generated_id_field.error_text = None

            # Now include both patient number and study number in the ID
            internal_suffix = f"{modality}.{study_index}||{patient_part}"
            generated_id = f"{PREFIX}^{project_id}||{internal_suffix}"

            self.generated_id_field.value = generated_id

        except Exception as e:
            self.update_status(f"Error generating ID: {e}")
            self.generated_id_field.value = ""
            self.generated_id_field.error_text = "Error during generation"
            traceback.print_exc()

    def update_status(self, message):
        """Safely updates the status list from any thread."""
        if self.page:
            def _update():
                self.status_list.controls.append(ft.Text(str(message), selectable=True))
                self.page.update()

            try:
                _update()
            except Exception as e:
                print(f"Error updating status (page might be closed or thread issue): {e}")

    def update_progress(self, value: float):
        """Safely updates the progress bar value from any thread."""
        if self.page and self.progress_bar:
            def _update():
                self.progress_bar.value = value
                self.page.update()
            try:
                _update()
            except Exception as e:
                print(f"Error updating progress bar (page might be closed or thread issue): {e}")

    def on_folder_result(self, e: ft.FilePickerResultEvent):
        target_control = None
        status_prefix = ""
        is_metadata_folder = False

        if e.control == self.input_picker:
            target_control = self.input_folder_path
            status_prefix = "Input folder"
        elif e.control == self.original_output_picker:
            target_control = self.original_output_folder_path
            status_prefix = "Original output folder"
        elif e.control == self.anonymized_output_picker:
            target_control = self.anonymized_output_folder_path
            status_prefix = "Anonymized output folder"
        elif e.control == self.metadata_picker:
            target_control = self.metadata_folder_path
            status_prefix = "Metadata folder"
            is_metadata_folder = True

        if target_control:
            path_selected = e.path
            if path_selected and os.path.isdir(path_selected):
                target_control.value = path_selected
                self.update_status(f"{status_prefix} set: {path_selected}")
                if is_metadata_folder:
                    self.first_name_field.value = ""
                    self.last_name_field.value = ""
                    self.patient_number_field.value = ""
                    self.surname_search_field.value = ""
                    self.search_results_dropdown.options = []
                    self.search_results_dropdown.value = None
                    self.search_results_dropdown.visible = False
                    self._update_patient_number_suggestion()
            elif path_selected:
                target_control.value = f"Invalid selection (not a folder)"
                self.update_status(f"{status_prefix} selection error: Not a valid folder.")
            else:
                self.update_status(f"{status_prefix} selection cancelled.")
        else:
            self.update_status("Error: Unknown folder picker result.")

        self.validate_inputs()
        if self.page: self.page.update()

    def validate_inputs(self, e=None):
        """Enable start button only if all required fields and paths are valid."""
        input_ok = os.path.isdir(self.input_folder_path.value)
        original_out_ok = os.path.isdir(self.original_output_folder_path.value)
        anon_out_ok = os.path.isdir(self.anonymized_output_folder_path.value)
        meta_ok = os.path.isdir(self.metadata_folder_path.value)

        first_name_ok = bool(self.first_name_field.value.strip())
        last_name_ok = bool(self.last_name_field.value.strip())
        generated_id_ok = bool(self.generated_id_field.value.strip()) and self.generated_id_field.error_text is None

        patient_number_str = self.patient_number_field.value.strip()
        patient_number_ok = bool(patient_number_str) and re.match(r"Pat\d+", patient_number_str, re.IGNORECASE) is not None
        if patient_number_str and not patient_number_ok:
            self.patient_number_field.error_text = "Use PatXXX format"
        else:
            self.patient_number_field.error_text = None

        modality_selected = self.modality_radio_group.value is not None
        other_modality_ok = not (self.modality_radio_group.value == "Other") or bool(self.other_modality_field.value.strip())
        modality_ok = modality_selected and other_modality_ok

        project_selected = self.project_dropdown.value is not None
        other_project_ok = not (self.project_dropdown.value == "Other") or bool(self.custom_project_field.value.strip())
        project_ok = project_selected and other_project_ok

        all_ok = (
            input_ok and original_out_ok and anon_out_ok and meta_ok and
            first_name_ok and last_name_ok and generated_id_ok and
            modality_ok and project_ok and patient_number_ok
        )

        self.start_button.disabled = not all_ok
        if self.page: self.page.update()

    def build_metadata_form(self):
        """Creates the layout for patient/study info, including search and patient number."""
        return ft.Column([
            ft.Row([
                ft.Column([ft.Text("Project:"), self.project_dropdown, self.custom_project_field], expand=1),
            ], alignment=ft.MainAxisAlignment.START),
            ft.Row([
                self.surname_search_field,
                self.search_results_dropdown,
            ], alignment=ft.MainAxisAlignment.START),
            ft.Row([
                self.first_name_field,
                self.last_name_field,
                self.patient_number_field,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                ft.Column([ft.Text("Modality:"), self.modality_radio_group, self.other_modality_field], expand=1),
                ft.Column([ft.Text("Study Number:"), self.study_number_field], expand=0, width=160),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START),
            self.generated_id_field,
        ])

    def collect_metadata(self):
        """Gathers all user inputs from the form fields and returns a dictionary."""
        metadata = {
            "input_folder": self.input_folder_path.value if os.path.isdir(self.input_folder_path.value) else "",
            "original_output_folder": self.original_output_folder_path.value if os.path.isdir(self.original_output_folder_path.value) else "",
            "anonymized_output_folder": self.anonymized_output_folder_path.value if os.path.isdir(self.anonymized_output_folder_path.value) else "",
            "metadata_folder": self.metadata_folder_path.value if os.path.isdir(self.metadata_folder_path.value) else "",
            "first_name": self.first_name_field.value.strip(),
            "last_name": self.last_name_field.value.strip(),
            "study_number": self.study_number_field.value.strip(),
            "generated_id": self.generated_id_field.value.strip(),
            "patient_number_str": self.patient_number_field.value.strip(),
            "study_date": None
        }

        project_id = self.project_dropdown.value
        if project_id == "Other":
            metadata["project_id"] = self.custom_project_field.value.strip()
        else:
            metadata["project_id"] = project_id if project_id else ""

        modality = self.modality_radio_group.value
        if modality == "Other":
            other_modality_val = self.other_modality_field.value.strip().upper()
            metadata["modality"] = other_modality_val if other_modality_val else "OTHER"
        else:
            metadata["modality"] = modality if modality else ""

        required_for_processing = ["input_folder", "original_output_folder", "anonymized_output_folder", "metadata_folder",
                                   "first_name", "last_name", "generated_id", "patient_number_str", "project_id", "modality"]
        for key in required_for_processing:
            if not metadata.get(key):
                print(f"Warning: Metadata collection missing value for '{key}'")

        return metadata

    def start_processing(self, e):
        """Handles the start button click: collects data and starts processing in a thread."""
        self.status_list.controls.clear()
        self.update_status("Collecting inputs...")
        self.start_button.disabled = True
        self.progress_ring.visible = True
        self.progress_bar.value = 0
        self.progress_bar.visible = True
        if self.page: self.page.update()

        metadata = self.collect_metadata()

        self.validate_inputs()
        if self.start_button.disabled:
            missing_details = "Check required fields (folders, names, project, modality, patient# format) and generated ID."
            self.update_status(f"ERROR: Cannot start. {missing_details}")
            self.progress_ring.visible = False
            self.progress_bar.visible = False
            if self.page: self.page.update()
            return

        self.update_status("Starting processing in background...")
        self.progress_ring.visible = False
        if self.page: self.page.update()

        thread = threading.Thread(target=self._run_processing_thread, args=(metadata,), daemon=True)
        thread.start()

    def _run_processing_thread(self, metadata):
        """Target function for the processing thread."""
        try:
            success = process_patient_study(
                metadata,
                status_callback=self.update_status,
                progress_callback=self.update_progress
            )
            if success:
                self.update_status("--- Processing Finished Successfully ---")
            else:
                self.update_status("--- Processing Finished with Errors (see log) ---")

        except Exception as ex:
            error_detail = traceback.format_exc()
            self.update_status(f"An unexpected critical error occurred: {ex}")
            print(f"Critical error during processing thread:\n{error_detail}")
        finally:
            if self.page:
                def _finalize_ui():
                    self.start_button.disabled = False
                    self.progress_ring.visible = False
                    self.progress_bar.visible = False
                    self.validate_inputs()
                    self.page.update()
                try:
                    _finalize_ui()
                except Exception as e:
                    print(f"Error finalizing UI (page might be closed or thread issue): {e}")

    def build(self, page: ft.Page):
        self.page = page
        page.title = "DICOM Anonymizer & Copier"
        page.window_width = 850
        page.window_height = 900
        page.padding = 15
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        page.overlay.extend([
            self.input_picker,
            self.original_output_picker,
            self.anonymized_output_picker,
            self.metadata_picker
        ])

        page.add(
            ft.Column(
                [
                    ft.Text("DICOM Anonymizer & Copier", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),

                    ft.Text("Folder Selection", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Select Input Folder...", icon=ft.icons.FOLDER_OPEN, on_click=lambda e: self.pick_folder(e, self.input_picker, "Select Input DICOM Folder")),
                        self.input_folder_path,
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Row([
                        ft.ElevatedButton("Select Output Folder (Originals)...", icon=ft.icons.FOLDER_COPY, on_click=lambda e: self.pick_folder(e, self.original_output_picker, "Select Output Folder for Originals")),
                        self.original_output_folder_path,
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Row([
                        ft.ElevatedButton("Select Output Folder (Anonymized)...", icon=ft.icons.FOLDER_SPECIAL, on_click=lambda e: self.pick_folder(e, self.anonymized_output_picker, "Select Output Folder for Anonymized")),
                        self.anonymized_output_folder_path,
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Row([
                        ft.ElevatedButton("Select Metadata Table Folder...", icon=ft.icons.TABLE_CHART, on_click=lambda e: self.pick_folder(e, self.metadata_picker, "Select Folder for Metadata CSV")),
                        self.metadata_folder_path,
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Divider(),

                    ft.Text("Patient & Study Information", size=18, weight=ft.FontWeight.BOLD),
                    self.build_metadata_form(),
                    ft.Divider(),

                    ft.Text("Status Log:", weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=self.status_list,
                        border=ft.border.all(1, ft.colors.OUTLINE),
                        border_radius=ft.border_radius.all(5),
                        padding=10,
                        expand=True
                    ),
                    ft.Row(
                        [
                            self.progress_ring,
                            self.progress_bar,
                            self.start_button
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ],
                expand=True,
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=10
            )
        )
        self.validate_inputs()
        self._update_patient_number_suggestion()
        page.update()

def main(page: ft.Page):
    try:
        import pydicom
        import shutil
        import csv
        import pathlib
        import re
        import threading
        import traceback
    except ImportError as e:
        print(f"Error: Missing required library. Please install dependencies. Missing: {e.name}")
        page.title = "Dependency Error"
        page.add(ft.Text(f"Error: Missing required library: {e.name}. Please install it (e.g., pip install pydicom).", color=ft.colors.RED, size=16))
        page.update()
        return

    app = DicomAnonymizerApp()
    app.build(page)

if __name__ == "__main__":
    ft.app(target=main)