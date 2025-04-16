import flet as ft
import os
import pydicom
import os
import concurrent.futures
# Import the logic from the other file


def anonymize_dicom_file(input_path, output_path):
    """
    Anonymizes a single DICOM file and saves it to the output path.

    Args:
        input_path (str): Path to the input DICOM file.
        output_path (str): Path where the anonymized DICOM file will be saved.

    Returns:
        bool: True if anonymization was successful, False otherwise.
    """
    try:
        ds = pydicom.dcmread(input_path)

        # --- Anonymization Steps based on pydicom example ---

        # 1. Define callback functions
        def person_names_callback(dataset, data_element):
            if data_element.VR == "PN":
                data_element.value = "ANONYMIZED" # Replace Person Names

        def curves_callback(dataset, data_element):
            # Example: Remove curve data (0x50xx, GGGG) elements
            # Adjust group number if necessary based on your data
            if data_element.tag.group & 0xFF00 == 0x5000:
                 del dataset[data_element.tag]

        # 2. Modify specific tags directly
        if "PatientID" in ds:
            ds.PatientID = "ANON_ID" # Replace Patient ID
        if "PatientBirthDate" in ds:
            # Keep birth date format valid but anonymize
            # Check if it has a value first
            if ds.PatientBirthDate:
                 ds.PatientBirthDate = "19000101" # Replace Birth Date
            else:
                 # If empty, ensure it remains empty or set a default if required
                 ds.PatientBirthDate = "" # Or "19000101" if a value is mandatory

        # Add other tags to clear or modify as needed
        tags_to_clear = [
            'PatientSex',
            'PatientAge',
            'PatientAddress',
            'PatientTelephoneNumbers',
            'ReferringPhysicianName',
            'PerformingPhysicianName',
            'OperatorsName',
            'InstitutionName',
            'InstitutionAddress',
            # 'StudyDescription',
            # 'SeriesDescription',
            'PatientComments',
            'RequestingPhysician',
            'OtherPatientIDs',
            'OtherPatientNames',
            'MedicalRecordLocator',
            'EthnicGroup',
            'Occupation',
            'AdditionalPatientHistory',
            # Add more tags here if necessary
        ]
        for tag_name in tags_to_clear:
             if tag_name in ds:
                 # Check if the element has a 'value' attribute before clearing
                 if hasattr(ds[tag_name], 'value'):
                     ds[tag_name].value = "" # Clear the value

        # 3. Apply callbacks to walk through the dataset
        ds.walk(person_names_callback)
        # ds.walk(curves_callback) # Uncomment if you need to remove curves

        # 4. Remove private tags
        ds.remove_private_tags()

        # 5. Handle potentially problematic optional tags (Type 3)
        # Using delattr is safer as it checks existence
        if hasattr(ds, "OtherPatientIDs"):
            delattr(ds, "OtherPatientIDs")
        if hasattr(ds, "OtherPatientIDsSequence"):
             # Sequences need 'del ds.SequenceName'
             if "OtherPatientIDsSequence" in ds:
                 del ds.OtherPatientIDsSequence

        # --- Saving the anonymized file ---

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        # Save the modified dataset
        # write_like_original=False ensures pydicom handles meta info correctly
        ds.save_as(output_path, write_like_original=False)
        print(f"Successfully anonymized '{input_path}' to '{output_path}'")
        return True

    except Exception as e:
        print(f"Error anonymizing file '{input_path}': {e}")
        return False


def process_folder(input_folder, output_folder, status_callback=None):
    """
    Recursively finds DICOM files (including extensionless) in the input folder,
    anonymizes them, and saves them to the output folder, preserving the
    directory structure.

    Args:
        input_folder (str): Path to the root folder containing DICOM files.
        output_folder (str): Path to the root folder where anonymized files will be saved.
        status_callback (callable, optional): A function to call with status updates.
                                              It should accept a single string argument.
    """
    if not os.path.isdir(input_folder):
        if status_callback:
            status_callback(f"Error: Input path '{input_folder}' is not a valid directory.")
        else:
            print(f"Error: Input path '{input_folder}' is not a valid directory.")
        return

    # Step 1: Collect all potential DICOM file paths recursively
    dicom_files = []
    if status_callback:
        status_callback("Scanning for DICOM files...")
    for root, _, files in os.walk(input_folder):
        for filename in files:
            # Check if it ends with .dcm OR has no extension (no dot in name)
            is_potential_dicom = (
                filename.lower().endswith(".dcm") or
                '.' not in filename
            )
            if is_potential_dicom:
                full_path = os.path.join(root, filename)
                # Double-check it's actually a file, not a directory named without a dot
                if os.path.isfile(full_path):
                    dicom_files.append(full_path)

    if not dicom_files:
        if status_callback:
            status_callback("No potential DICOM files (.dcm or extensionless) found.")
        else:
            print("No potential DICOM files (.dcm or extensionless) found.")
        return
    else:
         if status_callback:
             status_callback(f"Found {len(dicom_files)} potential DICOM files. Starting processing...")

    # Step 2: Map paths to remove file names and keep only folder subfolder structure
    subfolder_paths = []
    for file_path in dicom_files:
        rel_dir = os.path.relpath(os.path.dirname(file_path), input_folder)
        subfolder_paths.append(rel_dir)

    # Step 3: Get all unique folder subfolder structures (excluding ".")
    unique_subfolders = set([p for p in subfolder_paths if p != "."])

    # Step 4: Recreate subfolder structure in output folder
    for subfolder in unique_subfolders:
        out_subfolder = os.path.join(output_folder, subfolder)
        if not os.path.exists(out_subfolder):
            try:
                os.makedirs(out_subfolder, exist_ok=True)
                if status_callback:
                    status_callback(f"Created output subfolder: {out_subfolder}")
            except Exception as e:
                if status_callback:
                    status_callback(f"ERROR: Could not create output subfolder '{out_subfolder}': {e}")

    # Step 5: Anonymize all files and copy to analogous folders in output
    file_count = 0
    anonymized_count = 0
    for file_path in dicom_files:
        rel_dir = os.path.relpath(os.path.dirname(file_path), input_folder)
        filename = os.path.basename(file_path)
        # Step 6: If only one folder (root), put dicoms directly into output folder
        if rel_dir == "." or len(unique_subfolders) == 0:
            out_path = os.path.join(output_folder, filename)
        else:
            out_path = os.path.join(output_folder, rel_dir, filename)
        if status_callback:
            status_callback(f"Processing: '{file_path}' -> '{out_path}'")
        if anonymize_dicom_file(file_path, out_path):
            anonymized_count += 1
        else:
            if status_callback:
                status_callback(f"Failed: Anonymization error for '{file_path}'")
        file_count += 1

    summary = f"Anonymization complete. Processed {file_count} potential DICOM files. Successfully anonymized {anonymized_count} files."
    if status_callback:
        status_callback(summary)
    else:
        print(summary)


class DicomAnonymizerApp:
    def __init__(self):
        self.input_folder_path = ft.Text("No input folder selected")
        self.output_folder_path = ft.Text("No output folder selected")
        self.status_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        self.start_button = ft.ElevatedButton(
            text="Start Anonymization",
            on_click=self.start_processing,
            disabled=True # Disabled until paths are selected
        )
        self.input_picker = ft.FilePicker(on_result=self.on_input_folder_result)
        self.output_picker = ft.FilePicker(on_result=self.on_output_folder_result)
        self.page = None # To store page reference

    def update_status(self, message):
        """Safely updates the status list."""
        if self.page:
            self.status_list.controls.append(ft.Text(message))
            self.page.update()

    def pick_input_folder(self, e):
        self.input_picker.get_directory_path("Select Input DICOM Folder")

    def pick_output_folder(self, e):
        self.output_picker.get_directory_path("Select Output Folder for Anonymized Files")

    def on_input_folder_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.input_folder_path.value = e.path
            self.update_status(f"Input folder set: {e.path}")
        else:
            self.input_folder_path.value = "Input folder selection cancelled"
            self.update_status("Input folder selection cancelled.")
        self.check_paths_and_enable_button()
        self.page.update()

    def on_output_folder_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.output_folder_path.value = e.path
            self.update_status(f"Output folder set: {e.path}")
        else:
            self.output_folder_path.value = "Output folder selection cancelled"
            self.update_status("Output folder selection cancelled.")
        self.check_paths_and_enable_button()
        self.page.update()

    def check_paths_and_enable_button(self):
        """Enable start button only if both paths are valid directories."""
        input_ok = os.path.isdir(self.input_folder_path.value)
        output_selected = self.output_folder_path.value not in ["No output folder selected", "Output folder selection cancelled"]

        self.start_button.disabled = not (input_ok and output_selected)

    def start_processing(self, e):
        """Handles the start button click."""
        self.status_list.controls.clear() # Clear previous status
        self.update_status("Starting...")
        self.start_button.disabled = True # Disable button during processing
        self.page.update()

        input_path = self.input_folder_path.value
        output_path = self.output_folder_path.value

        if not os.path.isdir(input_path) or not output_path:
             self.update_status("Error: Invalid input or output path.")
             self.start_button.disabled = False # Re-enable button
             self.page.update()
             return

        try:
            process_folder(input_path, output_path, status_callback=self.update_status)
        except Exception as ex:
            self.update_status(f"An unexpected error occurred during processing: {ex}")
        finally:
            self.start_button.disabled = False
            self.page.update()

    def build(self, page: ft.Page):
        self.page = page # Store page reference
        page.title = "DICOM Anonymizer Tool"
        page.window_width = 700
        page.window_height = 600
        page.padding = 15

        # Add pickers to overlay
        page.overlay.append(self.input_picker)
        page.overlay.append(self.output_picker)

        page.add(
            ft.Column(
                [
                    ft.Text("DICOM Anonymizer", size=24, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.ElevatedButton("Select Input Folder...", on_click=self.pick_input_folder),
                            self.input_folder_path,
                        ],
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.Row(
                        [
                            ft.ElevatedButton("Select Output Folder...", on_click=self.pick_output_folder),
                            self.output_folder_path,
                        ],
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.Divider(),
                    ft.Text("Status Log:", weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=self.status_list,
                        border=ft.border.all(1, ft.colors.BLACK26),
                        border_radius=ft.border_radius.all(5),
                        padding=10,
                        expand=True
                    ),
                    ft.Row(
                        [self.start_button],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                expand=True
            )
        )
        self.check_paths_and_enable_button()
        page.update()


def main(page: ft.Page):
    app = DicomAnonymizerApp()
    app.build(page)

if __name__ == "__main__":
    try:
        import pydicom
    except ImportError:
        print("Error: pydicom library is required. Please install it using: pip install pydicom")
        exit()

    ft.app(target=main)