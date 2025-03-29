import flet as ft
import os
import json
import datetime
import uuid
import asyncio
import traceback
from flet_audio_recorder import AudioRecorder, AudioEncoder, AudioRecorderState

class PatientApp:
    def __init__(self):
        self.database_path = ""
        self.patient_data = {
            "patient_id": "",
            "name": "",
            "surname": "",
            "date": "",
            "initial_description": "",
            "scintigraphy": "",
            "fdg_pet": "",
            "additional_notes": ""  # Added new field for additional notes
        }
        self.audio_rec = None
        self.save_task = None
        self.original_patient_id = None
        self.page = None  # Store page reference
        self.status_clear_task = None  # Add a reference to the status clear task
        self.search_type = "id"  # Default search type is by ID
        self.active_dialog = None  # Track active dialog
        self.show_fdg_pet = False  # Toggle state for FDG PET visibility
        self.show_additional_notes = False  # Toggle state for Additional Notes visibility
        
    async def main(self, page: ft.Page):
        # Store reference to page
        self.page = page
        
        # Page setup
        page.title = "Patient Audio Recording System"
        page.window_width = 1000
        page.window_height = 800
        page.padding = 20
        page.theme_mode = ft.ThemeMode.LIGHT
        
        # Setup directory picker
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picker_result)
        page.overlay.append(self.dir_picker)
        
        # Audio recorder setup
        self.audio_rec = AudioRecorder(
            audio_encoder=AudioEncoder.WAV,
            suppress_noise=True,
            cancel_echo=True,
            auto_gain=True,
            on_state_changed=self.handle_audio_state_change
        )
        page.overlay.append(self.audio_rec)
        
        # Enhanced search functionality with type selection
        self.search_text = ft.TextField(
            label="Search for patient",
            expand=True,
            on_change=self.on_search_change,
            on_focus=self.on_search_focus,  # Added to handle focus event
            hint_text="Click to see all patients or type to search"  # Added hint text
        )
    
        # Radio buttons for search type
        self.search_type_group = ft.RadioGroup(
            value=self.search_type,
            content=ft.Row([
                ft.Radio(value="id", label="ID"),
                ft.Radio(value="name", label="Name/Surname"),
                ft.Radio(value="all", label="All Fields")
            ]),
            on_change=self.on_search_type_change
        )
        
        self.search_results = ft.ListView(
            height=200,
            visible=False
        )
        
        # Database path field
        self.db_path_field = ft.TextField(
            label="Database Folder Path",
            value=self.database_path,
            expand=True,
            on_change=self.on_db_path_change
        )
        
        browse_button = ft.ElevatedButton(
            text="Browse",
            on_click=self.pick_directory
        )
        
        # Patient information fields
        self.name_field = ft.TextField(
            label="Patient Name",
            value=self.patient_data["name"],
            on_change=self.on_name_change,
            expand=True
        )
        
        self.surname_field = ft.TextField(
            label="Patient Surname",
            value=self.patient_data["surname"],
            on_change=self.on_surname_change,
            expand=True
        )
        
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.date_field = ft.TextField(
            label="Date",
            value=today,
            on_change=self.on_date_change
        )
        
        self.patient_id_field = ft.TextField(
            label="Patient ID",
            value=self.patient_data["patient_id"],
            read_only=False,  # Changed to allow manual editing
            on_change=self.on_patient_id_change  # Added change handler
        )
        
        generate_id_button = ft.ElevatedButton(
            text="Generate ID",
            on_click=self.generate_patient_id
        )
        
        # Text areas for descriptions - make them larger but not too large
        self.initial_description = ft.TextField(
            label="Initial Description",
            multiline=True,
            min_lines=4,  # Slightly reduced to save space
            max_lines=8,  # Slightly reduced to save space
            value=self.patient_data["initial_description"],
            on_change=self.on_initial_desc_change,
            expand=True
        )
        
        self.scintigraphy = ft.TextField(
            label="Scintigraphy",
            multiline=True,
            min_lines=4,  # Slightly reduced to save space
            max_lines=8,  # Slightly reduced to save space
            value=self.patient_data["scintigraphy"],
            on_change=self.on_scintigraphy_change,
            expand=True
        )
        
        self.fdg_pet = ft.TextField(
            label="FDG PET",
            multiline=True,
            min_lines=4,  # Slightly reduced to save space
            max_lines=8,  # Slightly reduced to save space
            value=self.patient_data["fdg_pet"],
            on_change=self.on_fdg_pet_change,
            expand=True,
            visible=self.show_fdg_pet  # Toggle visibility based on state
        )
        
        # Add additional notes text area - also larger
        self.additional_notes = ft.TextField(
            label="Additional Notes",
            multiline=True,
            min_lines=4,  # Slightly reduced to save space
            max_lines=8,  # Slightly reduced to save space
            value=self.patient_data["additional_notes"],
            on_change=self.on_additional_notes_change,
            expand=True,
            visible=self.show_additional_notes  # Toggle visibility based on state
        )
        
        # Recording controls
        self.record_button = ft.ElevatedButton(
            text="Start Recording",
            icon=ft.Icons.MIC,  # Updated from lowercase
            on_click=self.start_recording,
            bgcolor=ft.Colors.GREEN,  # Updated from lowercase
            width=150,  # Make button larger
            height=50  # Make button larger
        )
        
        self.stop_button = ft.ElevatedButton(
            text="Stop Recording",
            icon=ft.Icons.STOP,  # Updated from lowercase
            on_click=self.stop_recording,
            bgcolor=ft.Colors.RED,  # Updated from lowercase
            disabled=True,
            width=150,  # Make button larger
            height=50  # Make button larger
        )
        
        # Status bar
        self.status_text = ft.Text("")
        
        # Clear button
        clear_button = ft.ElevatedButton(
            text="Clear Form",
            on_click=self.clear_form
        )
        
        # Add Save button
        save_button = ft.ElevatedButton(
            text="Save Patient Data",
            icon=ft.icons.SAVE,
            on_click=self.save_button_clicked,
            bgcolor=ft.Colors.BLUE
        )
        
        # Add USG prefix field for audio recordings
        self.recording_prefix = ft.TextField(
            label="Recording Prefix",
            value="USG",
            width=100,
            height=40
        )
        
        # Layout the app with a main scrollable area
        # Use a Column with a ScrollableControl to make everything scrollable
        page.add(
            # Top bar with search - keep this outside of scrollable area
            ft.Row([
                ft.Text("Patient Audio Recording System", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(width=10),
                ft.Column([
                    self.search_text,
                    self.search_type_group
                ], spacing=5)
            ]),
            self.search_results,
            ft.Divider(),
            
            # Make everything else scrollable
            ft.Container(
                content=ft.Column(
                    [
                        # Database path selector
                        ft.Row([
                            self.db_path_field,
                            browse_button
                        ]),
                        
                        # Patient info
                        ft.Row([
                            self.name_field,
                            self.surname_field
                        ]),
                        
                        ft.Row([
                            self.date_field,
                            self.patient_id_field,
                            generate_id_button
                        ]),
                        
                        # Description fields with more spacing
                        ft.Container(
                            content=ft.Text("Patient Notes", size=16, weight=ft.FontWeight.BOLD),
                            margin=ft.margin.only(top=10, bottom=5)
                        ),
                        ft.Container(content=self.initial_description, margin=ft.margin.only(bottom=8)),
                        ft.Container(content=self.scintigraphy, margin=ft.margin.only(bottom=8)),
                        ft.Container(content=self.fdg_pet, margin=ft.margin.only(bottom=8)),
                        ft.Container(content=self.additional_notes, margin=ft.margin.only(bottom=8)),
                        
                        # Toggle switches for FDG PET and Additional Notes visibility
                        ft.Row([
                            ft.Switch(
                                label="Show FDG PET",
                                value=self.show_fdg_pet,
                                on_change=self.toggle_fdg_pet_visibility
                            ),
                            ft.Switch(
                                label="Show Additional Notes",
                                value=self.show_additional_notes,
                                on_change=self.toggle_additional_notes_visibility
                            )
                        ]),
                        
                        # Audio controls with recording prefix - make sure these are visible
                        ft.Container(
                            content=ft.Row([
                                self.recording_prefix,
                                self.record_button,
                                self.stop_button,
                                ft.Container(width=20),
                                clear_button
                            ]),
                            margin=ft.margin.only(top=10, bottom=10)
                        ),
                        
                        # Save button at the bottom
                        ft.Row([
                            save_button,
                        ]),
                        
                        # Status bar
                        self.status_text,
                        
                        # Add some bottom padding to ensure everything is visible
                        ft.Container(height=20)
                    ],
                    scroll=ft.ScrollMode.AUTO  # Enable scrolling
                ),
                height=page.window_height - 150,  # Reserve space for the top bar
                expand=True
            )
        )
        
        # Start the autosave task
        page.on_disconnect = self.cleanup
        try:
            self.save_task = asyncio.create_task(self.auto_save_task())
            print("Autosave task started successfully")
        except Exception as ex:
            print(f"Error starting autosave task: {str(ex)}")
            traceback.print_exc()

    async def cleanup(self, e):
        """Cleanup when app disconnects"""
        if self.save_task and not self.save_task.done():
            self.save_task.cancel()
        
    async def handle_audio_state_change(self, e):
        """Handle audio recorder state changes"""
        print(f"Audio state changed: {e.data}")
        state = e.state
        if state == AudioRecorderState.RECORDING:
            self.record_button.disabled = True
            self.stop_button.disabled = False
        elif state == AudioRecorderState.STOPPED:
            self.record_button.disabled = False
            self.stop_button.disabled = True
        
        # Use self.page instead of e.page
        if self.page:
            self.page.update()
        
    def on_db_path_change(self, e):
        """Handle database path changes"""
        self.database_path = e.control.value
        
    async def pick_directory(self, e):
        """Open directory picker to select database location"""
        # Use FilePicker instead of client_storage
        if self.dir_picker:
            self.dir_picker.get_directory_path()
        
    def on_dir_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle directory picker result"""
        if e.path:
            self.database_path = e.path
            self.db_path_field.value = e.path
            
            # Use self.page instead of e.page and don't use await
            if self.page:
                self.page.update()
                self.update_status("Database path set to: " + e.path)
    
    def on_name_change(self, e):
        """Handle name field changes"""
        self.patient_data["name"] = e.control.value
        
    def on_surname_change(self, e):
        """Handle surname field changes"""
        self.patient_data["surname"] = e.control.value
        
    def on_date_change(self, e):
        """Handle date field changes"""
        self.patient_data["date"] = e.control.value
        
    def on_initial_desc_change(self, e):
        """Handle initial description changes"""
        self.patient_data["initial_description"] = e.control.value
        
    def on_scintigraphy_change(self, e):
        """Handle scintigraphy changes"""
        self.patient_data["scintigraphy"] = e.control.value
        
    def on_fdg_pet_change(self, e):
        """Handle FDG PET changes"""
        self.patient_data["fdg_pet"] = e.control.value
    
    def on_additional_notes_change(self, e):
        """Handle additional notes changes"""
        self.patient_data["additional_notes"] = e.control.value
    
    def on_patient_id_change(self, e):
        """Handle manual patient ID changes"""
        self.patient_data["patient_id"] = e.control.value
    
    def generate_patient_id(self, e):
        """Generate a unique patient ID based on date and name/surname if available"""
        try:
            date_str = self.date_field.value.replace("-", "")
            
            # Fix potential IndexError by checking if the string has content first
            if self.patient_data["name"]:
                name_part = self.patient_data["name"][:2].upper()
            else:
                name_part = "XX"
                
            if self.patient_data["surname"]:
                surname_part = self.patient_data["surname"][:2].upper()
            else:
                surname_part = "XX"
                
            unique_part = str(uuid.uuid4())[:5]
            
            suggested_id = f"{date_str}-{name_part}{surname_part}-{unique_part}"
            
            # Check if ID already exists and suggest modification if it does
            if self.database_path:
                patient_folder = os.path.join(self.database_path, suggested_id)
                if os.path.exists(patient_folder):
                    # Generate an alternative
                    alt_unique_part = str(uuid.uuid4())[:5]
                    suggested_id = f"{date_str}-{name_part}{surname_part}-{alt_unique_part}"
                    self.update_status(f"Original ID exists. Suggested alternative: {suggested_id}")
                    
                    # Create and show dialog for ID conflict
                    dialog = ft.AlertDialog(
                        title=ft.Text("Patient ID Exists"),
                        content=ft.Text(f"Patient ID already exists. Would you like to load the existing data?"),
                        actions=[
                            ft.TextButton("Yes", on_click=lambda e, pid=suggested_id: self.load_existing_patient(e, pid)),
                            ft.TextButton("No", on_click=self.close_dialog),
                        ],
                    )
                    self.show_dialog(dialog)
                    return
            
            # Set the suggested ID but allow user to modify
            self.patient_data["patient_id"] = suggested_id
            self.patient_id_field.value = suggested_id
            self.original_patient_id = None  # Reset original ID since this is a new one
            
            if self.page:
                self.page.update()
            self.update_status(f"Patient ID suggested: {suggested_id}. You can edit it if needed.")
            
        except Exception as ex:
            print(f"Error generating patient ID: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error generating patient ID: {str(ex)}")

    def show_dialog(self, dialog):
        """Helper method to safely show dialogs"""
        if self.page:
            self.active_dialog = dialog
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def close_dialog(self, e):
        """Close the dialog safely"""
        if self.page and self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
            self.active_dialog = None
    
    def load_existing_patient(self, e, patient_id):
        """Load existing patient data from ID conflict dialog"""
        # Close the dialog first
        self.close_dialog(e)
        # Now load the patient
        self.load_patient(e, patient_id)
    
    def start_recording(self, e):
        """Start audio recording"""
        try:
            if not self.patient_data["patient_id"]:
                self.update_status("Please generate a patient ID first")
                return
                
            if not self.database_path:
                self.update_status("Please set a database path first")
                return
                
            # Get the recording prefix
            prefix = self.recording_prefix.value.strip()
            if not prefix:
                prefix = "USG"  # Default to USG if empty
                
            # Create filename with timestamp and prefix
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            patient_folder = os.path.join(self.database_path, self.patient_data["patient_id"])
            filename = os.path.join(patient_folder, f"{prefix}_{timestamp}.wav")
            
            # Ensure the directory exists
            if not os.path.exists(patient_folder):
                os.makedirs(patient_folder)
            
            print(f"Starting recording to file: {filename}")
            
            # Explicitly check if recorder is initialized
            if self.audio_rec is None:
                self.update_status("Audio recorder not initialized")
                return
            
            # Create a result handler for recording
            def handle_recording_result(e):
                if e.data == "true":
                    self.update_status(f"Recording started. Saving to {filename}")
                else:
                    self.update_status("Failed to start recording")
            
            # Register a one-time handler for the result
            self.audio_rec.on_result = handle_recording_result
            
            # Start recording - don't pass callback directly
            self.audio_rec.start_recording(filename)
            print("Recording started")
        except Exception as ex:
            print(f"Error starting recording: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error starting recording: {str(ex)}")
    
    def stop_recording(self, e):
        """Stop audio recording"""
        try:
            print("Stopping recording...")
            
            # Explicitly check if recorder is initialized
            if self.audio_rec is None:
                self.update_status("Audio recorder not initialized")
                return
            
            # Create a result handler for stopping
            def handle_stop_result(e):
                output_path = e.data
                print(f"Recording stopped. Output path: {output_path}")
                if output_path and output_path != "null":
                    self.update_status(f"Recording saved to: {output_path}")
                else:
                    self.update_status("Recording stopped, but file was not saved")
            
            # Register a one-time handler for the result
            self.audio_rec.on_result = handle_stop_result
            
            # Stop recording without callback
            self.audio_rec.stop_recording()
        except Exception as ex:
            print(f"Error stopping recording: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error stopping recording: {str(ex)}")
    
    async def on_search_change(self, e):
        """Handle search field changes and show matching patients"""
        search_term = e.control.value.strip().lower()
        await self.perform_search(search_term)
    
    async def perform_search(self, search_term):
        """Perform search based on the current search type and term"""
        if not self.database_path or not os.path.exists(self.database_path):
            self.update_status("Please set a valid database path first")
            return
            
        # Even if search term is empty, we'll show all patients
        # This makes the dropdown work when just clicking the field
        
        # Search for matching patients
        matching_patients = []
        try:
            if os.path.exists(self.database_path):
                for folder in os.listdir(self.database_path):
                    folder_path = os.path.join(self.database_path, folder)
                    if os.path.isdir(folder_path):
                        json_file = os.path.join(folder_path, "patient_data.json")
                        if os.path.exists(json_file):
                            try:
                                with open(json_file, 'r') as f:
                                    data = json.load(f)
                                    
                                    # If search term is empty, include all patients
                                    if not search_term:
                                        matching_patients.append(data)
                                        continue
                                    
                                    # Match based on selected search type
                                    is_match = False
                                    
                                    if self.search_type == "id":
                                        # Search by ID only
                                        if search_term in data.get("patient_id", "").lower():
                                            is_match = True
                                            
                                    elif self.search_type == "name":
                                        # Search by name or surname
                                        if (search_term in data.get("name", "").lower() or
                                            search_term in data.get("surname", "").lower()):
                                            is_match = True
                                            
                                    else:  # "all" - search all fields
                                        if (search_term in data.get("patient_id", "").lower() or
                                            search_term in data.get("name", "").lower() or 
                                            search_term in data.get("surname", "").lower() or
                                            search_term in data.get("date", "").lower()):
                                            is_match = True
                                        
                                    if is_match:
                                        matching_patients.append(data)
                                        
                            except json.JSONDecodeError:
                                continue
                
            # Update the search results list
            self.search_results.controls.clear()
            
            if matching_patients:
                # Sort results for better display
                matching_patients.sort(key=lambda x: x.get('patient_id', ''))
                
                for patient in matching_patients:
                    patient_id = patient.get('patient_id', '')
                    name = patient.get('name', '')
                    surname = patient.get('surname', '')
                    date = patient.get('date', '')
                    
                    # Create a properly bound callback for each patient
                    # This is crucial - we need to create a new function for each patient ID
                    self.search_results.controls.append(
                        ft.ListTile(
                            title=ft.Text(f"{name} {surname}"),
                            subtitle=ft.Text(f"ID: {patient_id}, Date: {date}"),
                            # Fix the lambda with a default argument for proper binding
                            on_click=self.create_patient_loader(patient_id)
                        )
                    )
                self.search_results.visible = True
            else:
                self.search_results.visible = False
                if search_term:  # Only show "no matches" for actual searches
                    self.update_status(f"No matches found for '{search_term}'")
                
            if self.page:
                await self.page.update()
            
        except Exception as ex:
            print(f"Error searching patients: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error searching patients: {str(ex)}")
    
    def create_patient_loader(self, patient_id):
        """Create a callback function for loading a specific patient"""
        def load_this_patient(e):
            self.load_patient(e, patient_id)
        return load_this_patient
    
    async def on_search_focus(self, e):
        """Handle when search field gets focus - show all patients immediately"""
        print("Search field focused - loading all patients")
        
        # Clear any existing search term to ensure all patients are shown
        if self.search_text.value:
            self.search_text.value = ""
        
        if not self.database_path or not os.path.exists(self.database_path):
            self.update_status("Please set a valid database path first")
            return
        
        # Always show all patients when focusing
        try:
            await self.load_all_patients()
            print("All patients loaded successfully")
        except Exception as ex:
            print(f"Error loading patients on focus: {str(ex)}")
            traceback.print_exc()
            self.update_status("Error loading patient list")
    
    async def load_all_patients(self):
        """Load and display all available patients"""
        try:
            if not self.database_path or not os.path.exists(self.database_path):
                self.update_status("Please set a valid database path first")
                return
                
            all_patients = []
            patient_count = 0
            
            # Count directories first to give user feedback
            for item in os.listdir(self.database_path):
                if os.path.isdir(os.path.join(self.database_path, item)):
                    patient_count += 1
            
            if patient_count == 0:
                self.update_status("No patient records found in database")
                self.search_results.visible = False
                if self.page:
                    self.page.update()
                return
            
            self.update_status(f"Loading {patient_count} patient records...")
            
            # Now load the patient data
            for folder in os.listdir(self.database_path):
                folder_path = os.path.join(self.database_path, folder)
                if os.path.isdir(folder_path):
                    json_file = os.path.join(folder_path, "patient_data.json")
                    if os.path.exists(json_file):
                        try:
                            with open(json_file, 'r') as f:
                                data = json.load(f)
                                all_patients.append(data)
                        except json.JSONDecodeError:
                            print(f"Warning: Could not parse JSON in {json_file}")
                            continue
            
            # Update search results
            self.search_results.controls.clear()
            
            if all_patients:
                # Sort patients by ID for better display
                all_patients.sort(key=lambda x: x.get('patient_id', ''))
                
                for patient in all_patients:
                    patient_id = patient.get('patient_id', '')
                    name = patient.get('name', '')
                    surname = patient.get('surname', '')
                    
                    display_name = f"{name} {surname}"
                    if not display_name.strip():
                        display_name = f"Patient {patient_id}"
                    
                    self.search_results.controls.append(
                        ft.ListTile(
                            title=ft.Text(display_name),
                            subtitle=ft.Text(f"ID: {patient_id}, Date: {patient.get('date', '')}"),
                            on_click=self.create_patient_loader(patient_id)
                        )
                    )
                
                self.search_results.visible = True
                self.update_status(f"Found {len(all_patients)} patients")
            else:
                self.search_results.visible = False
                self.update_status("No patient data available")
                
            # Update the page to show the results
            if self.page:
                self.page.update()
                
        except Exception as ex:
            print(f"Error loading all patients: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error loading patients: {str(ex)}")
            # Ensure the results are hidden on error
            self.search_results.visible = False
            if self.page:
                self.page.update()
    
    def on_search_type_change(self, e):
        """Handle search type radio button changes"""
        self.search_type = e.value
        # If there's text in the search field, re-trigger the search
        if self.search_text.value:
            asyncio.create_task(self.perform_search(self.search_text.value))
    
    def load_patient(self, e, patient_id):
        """Load patient data when selected from search results"""
        try:
            if not patient_id or not self.database_path:
                return
                
            # We don't need to check for dialog here - that was causing the error
            # Instead, just close the search results
            self.search_results.visible = False
                
            patient_folder = os.path.join(self.database_path, patient_id)
            json_file = os.path.join(patient_folder, "patient_data.json")
            
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        
                    # Update the form fields
                    self.patient_data = data
                    self.name_field.value = data.get("name", "")
                    self.surname_field.value = data.get("surname", "")
                    self.date_field.value = data.get("date", "")
                    self.patient_id_field.value = data.get("patient_id", "")
                    self.initial_description.value = data.get("initial_description", "")
                    self.scintigraphy.value = data.get("scintigraphy", "")
                    self.fdg_pet.value = data.get("fdg_pet", "")
                    
                    # Add support for the new additional_notes field with fallback
                    self.additional_notes.value = data.get("additional_notes", "")
                    
                    # Remember the original ID to avoid warning when saving the same patient
                    self.original_patient_id = patient_id
                    
                    if self.page:
                        self.page.update()
                    self.update_status(f"Loaded patient: {data.get('name', '')} {data.get('surname', '')}")
                    
                except Exception as ex:
                    print(f"Error loading patient data: {str(ex)}")
                    traceback.print_exc()
                    self.update_status(f"Error loading patient data: {str(ex)}")
            else:
                self.update_status(f"Patient data file not found")
        except Exception as ex:
            print(f"Error in load_patient: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error loading patient: {str(ex)}")
    
    async def save_patient_data(self):
        """Save current patient data to JSON file"""
        try:
            if not self.patient_data["patient_id"] or not self.database_path:
                return False
                
            patient_folder = os.path.join(self.database_path, self.patient_data["patient_id"])
            
            # Check if patient folder exists, create if it doesn't
            if not os.path.exists(patient_folder):
                os.makedirs(patient_folder)
                
            # Save patient data
            json_file = os.path.join(patient_folder, "patient_data.json")
            
            print(f"Saving patient data to: {json_file}")
            
            with open(json_file, 'w') as f:
                json.dump(self.patient_data, f, indent=4)
            return True
        except Exception as ex:
            print(f"Error saving patient data: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error saving patient data: {str(ex)}")
            return False
    
    async def auto_save_task(self):
        """Periodically auto-save patient data"""
        print("Auto-save task started")
        # Add a flag for immediate save requests
        self.immediate_save_requested = False
        
        while True:
            try:
                if self.patient_data["patient_id"] and self.database_path:
                    should_save = False
                    
                    # Check if immediate save was requested
                    if self.immediate_save_requested:
                        print("Immediate save requested")
                        should_save = True
                        self.immediate_save_requested = False  # Reset the flag
                    else:
                        # Otherwise, it's a regular autosave
                        print("Performing regular auto-save...")
                        should_save = True
                    
                    if should_save:
                        save_result = await self.save_patient_data()
                        if save_result:
                            print("Save successful")
                            if self.immediate_save_requested == False:  # Only show for manual saves
                                self.update_status("Patient data saved successfully")
                            else:
                                # For autosaves, use a less intrusive message
                                self.update_status("Auto-saved patient data")
                        else:
                            print("Save returned False")
                            self.update_status("Failed to save patient data")
                else:
                    print("Skipping save - no patient ID or database path")
            except Exception as ex:
                print(f"Save error: {str(ex)}")
                traceback.print_exc()
                self.update_status(f"Error saving patient data: {str(ex)}")
                
            # Use a shorter sleep interval to be more responsive to immediate save requests
            await asyncio.sleep(1)  # Check more frequently, but only save at regular intervals
            
            # Add a counter for regular autosaves to happen every 4 seconds
            if not hasattr(self, 'autosave_counter'):
                self.autosave_counter = 0
            
            self.autosave_counter += 1
            # Reset counter after 4 iterations (4 seconds with 1-second sleep)
            if self.autosave_counter >= 4:
                self.autosave_counter = 0
    
    def save_button_clicked(self, e):
        """Save patient data when save button is clicked"""
        try:
            # Validate patient ID
            if not self.patient_data["patient_id"]:
                self.update_status("Please provide a patient ID before saving")
                return
            
            # Validate database path
            if not self.database_path:
                self.update_status("Please set a database path first")
                return
            
            # Force a save immediately without creating a new task
            # This sets up a flag that will trigger the save
            self.request_immediate_save()
            self.update_status("Saving patient data...")
            
        except Exception as ex:
            print(f"Error saving data: {str(ex)}")
            traceback.print_exc()
            self.update_status(f"Error saving data: {str(ex)}")
    
    def request_immediate_save(self):
        """Flag that we want an immediate save to happen"""
        self.immediate_save_requested = True
    
    def clear_form(self, e):
        """Clear all form fields"""
        self.patient_data = {
            "patient_id": "",
            "name": "",
            "surname": "",
            "date": datetime.date.today().strftime("%Y-%m-%d"),
            "initial_description": "",
            "scintigraphy": "",
            "fdg_pet": "",
            "additional_notes": ""  # Added new field
        }
        
        self.name_field.value = ""
        self.surname_field.value = ""
        self.date_field.value = datetime.date.today().strftime("%Y-%m-%d")
        self.patient_id_field.value = ""
        self.initial_description.value = ""
        self.scintigraphy.value = ""
        self.fdg_pet.value = ""
        self.additional_notes.value = ""  # Clear additional notes field
        self.original_patient_id = None
        
        if self.page:
            self.page.update()
        self.update_status("Form cleared")
    
    def update_status(self, message, temporary=False):
        """Update status message at the bottom of the page"""
        print(f"Status: {message}")
        
        if not self.page:
            print(f"Warning: Page reference is None, can't update UI status")
            return
            
        self.status_text.value = message
        self.page.update()
        
        if temporary:
            # Cancel any existing timer task
            if hasattr(self, 'status_clear_task') and self.status_clear_task:
                try:
                    self.status_clear_task.cancel()
                except:
                    pass
                
            # Schedule a new task to clear the status text after a delay
            self.schedule_status_clear()
    
    def schedule_status_clear(self):
        """Schedule clearing of status text using a background task"""
        async def clear_status_after_delay():
            try:
                await asyncio.sleep(3)  # Wait for 3 seconds
                if self.page:
                    self.status_text.value = ""
                    self.page.update()
            except asyncio.CancelledError:
                pass  # Task was cancelled, which is fine
            except Exception as ex:
                print(f"Error clearing status: {str(ex)}")
                
        # Create and store the task
        self.status_clear_task = asyncio.create_task(clear_status_after_delay())
    
    def toggle_fdg_pet_visibility(self, e):
        """Toggle visibility of FDG PET field"""
        self.show_fdg_pet = e.control.value
        self.fdg_pet.visible = self.show_fdg_pet
        if self.page:
            self.page.update()
    
    def toggle_additional_notes_visibility(self, e):
        """Toggle visibility of Additional Notes field"""
        self.show_additional_notes = e.control.value
        self.additional_notes.visible = self.show_additional_notes
        if self.page:
            self.page.update()


async def main(page: ft.Page):
    app = PatientApp()
    await app.main(page)

ft.app(target=main)