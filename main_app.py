import flet as ft
import os
import json
import datetime
import uuid
import asyncio
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
            "fdg_pet": ""
        }
        self.audio_rec = None
        self.save_task = None
        self.original_patient_id = None
        
    async def main(self, page: ft.Page):
        # Page setup
        page.title = "Patient Audio Recording System"
        page.window_width = 1000
        page.window_height = 800
        page.padding = 20
        page.theme_mode = ft.ThemeMode.LIGHT
        
        # Audio recorder setup
        self.audio_rec = AudioRecorder(
            audio_encoder=AudioEncoder.WAV,
            suppress_noise=True,
            cancel_echo=True,
            auto_gain=True,
            on_state_changed=self.handle_audio_state_change
        )
        page.overlay.append(self.audio_rec)
        
        # Search functionality
        self.search_text = ft.TextField(
            label="Search by name, surname or ID",
            expand=True,
            on_change=self.on_search_change
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
            read_only=True
        )
        
        generate_id_button = ft.ElevatedButton(
            text="Generate ID",
            on_click=self.generate_patient_id
        )
        
        # Text areas for descriptions
        self.initial_description = ft.TextField(
            label="Initial Description",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value=self.patient_data["initial_description"],
            on_change=self.on_initial_desc_change,
            expand=True
        )
        
        self.scintigraphy = ft.TextField(
            label="Scintigraphy",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value=self.patient_data["scintigraphy"],
            on_change=self.on_scintigraphy_change,
            expand=True
        )
        
        self.fdg_pet = ft.TextField(
            label="FDG PET",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value=self.patient_data["fdg_pet"],
            on_change=self.on_fdg_pet_change,
            expand=True
        )
        
        # Recording controls
        self.record_button = ft.ElevatedButton(
            text="Start Recording",
            icon=ft.icons.MIC,
            on_click=self.start_recording,
            bgcolor=ft.colors.GREEN
        )
        
        self.stop_button = ft.ElevatedButton(
            text="Stop Recording",
            icon=ft.icons.STOP,
            on_click=self.stop_recording,
            bgcolor=ft.colors.RED,
            disabled=True
        )
        
        # Status bar
        self.status_text = ft.Text("")
        
        # Clear button
        clear_button = ft.ElevatedButton(
            text="Clear Form",
            on_click=self.clear_form
        )
        
        # Layout the app
        page.add(
            # Top bar with search
            ft.Row([
                ft.Text("Patient Audio Recording System", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(width=10),
                self.search_text,
            ]),
            self.search_results,
            ft.Divider(),
            
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
            
            # Description fields
            ft.Text("Patient Notes", size=16, weight=ft.FontWeight.BOLD),
            self.initial_description,
            self.scintigraphy,
            self.fdg_pet,
            
            # Audio controls
            ft.Row([
                self.record_button,
                self.stop_button,
                ft.Container(width=20),
                clear_button
            ]),
            
            # Status bar
            self.status_text
        )
        
        # Start the autosave task
        self.save_task = asyncio.create_task(self.auto_save_task(page))
        
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
        await e.page.update_async()
        
    def on_db_path_change(self, e):
        """Handle database path changes"""
        self.database_path = e.control.value
        
    async def pick_directory(self, e):
        """Open directory picker to select database location"""
        directory = await e.page.client_storage.pick_dir_async()
        if directory:
            self.database_path = directory
            self.db_path_field.value = directory
            await e.page.update_async()
            await self.update_status("Database path set to: " + directory, e.page)
    
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
    
    async def generate_patient_id(self, e):
        """Generate a unique patient ID based on date and name"""
        if not self.patient_data["name"] or not self.patient_data["surname"]:
            await self.update_status("Please enter patient name and surname first", e.page)
            return
            
        date_str = self.date_field.value.replace("-", "")
        name_part = self.patient_data["name"][:2].upper()
        surname_part = self.patient_data["surname"][:2].upper()
        unique_part = str(uuid.uuid4())[:5]
        
        patient_id = f"{date_str}-{name_part}{surname_part}-{unique_part}"
        self.patient_data["patient_id"] = patient_id
        self.patient_id_field.value = patient_id
        self.original_patient_id = patient_id
        
        await e.page.update_async()
        await self.update_status(f"Patient ID generated: {patient_id}", e.page)
        
        # Check if patient folder exists and create if it doesn't
        if self.database_path:
            patient_folder = os.path.join(self.database_path, patient_id)
            if not os.path.exists(patient_folder):
                os.makedirs(patient_folder)
                await self.update_status(f"Created patient folder: {patient_folder}", e.page)
            else:
                await self.update_status(f"Patient folder already exists: {patient_folder}", e.page)
    
    async def start_recording(self, e):
        """Start audio recording"""
        if not self.patient_data["patient_id"]:
            await self.update_status("Please generate a patient ID first", e.page)
            return
            
        if not self.database_path:
            await self.update_status("Please set a database path first", e.page)
            return
            
        # Create filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        patient_folder = os.path.join(self.database_path, self.patient_data["patient_id"])
        filename = os.path.join(patient_folder, f"recording_{timestamp}.wav")
        
        # Ensure the directory exists
        if not os.path.exists(patient_folder):
            os.makedirs(patient_folder)
        
        # Start recording
        success = await self.audio_rec.start_recording_async(filename)
        
        if success:
            await self.update_status(f"Recording started. Saving to {filename}", e.page)
        else:
            await self.update_status("Failed to start recording", e.page)
    
    async def stop_recording(self, e):
        """Stop audio recording"""
        output_path = await self.audio_rec.stop_recording_async()
        
        if output_path:
            await self.update_status(f"Recording saved to: {output_path}", e.page)
        else:
            await self.update_status("Recording stopped, but file was not saved", e.page)
    
    async def on_search_change(self, e):
        """Handle search field changes and show matching patients"""
        search_term = e.control.value.strip().lower()
        if not search_term or len(search_term) < 2:
            self.search_results.visible = False
            await e.page.update_async()
            return
        
        if not self.database_path or not os.path.exists(self.database_path):
            await self.update_status("Please set a valid database path first", e.page)
            return
        
        # Search for matching patients
        matching_patients = []
        try:
            for folder in os.listdir(self.database_path):
                folder_path = os.path.join(self.database_path, folder)
                if os.path.isdir(folder_path):
                    json_file = os.path.join(folder_path, "patient_data.json")
                    if os.path.exists(json_file):
                        try:
                            with open(json_file, 'r') as f:
                                data = json.load(f)
                                
                                # Check if any field matches the search term
                                if (search_term in data.get("patient_id", "").lower() or
                                    search_term in data.get("name", "").lower() or 
                                    search_term in data.get("surname", "").lower() or
                                    search_term in data.get("date", "").lower()):
                                    
                                    matching_patients.append(data)
                        except json.JSONDecodeError:
                            continue
                            
            # Update the search results list
            self.search_results.controls.clear()
            if matching_patients:
                for patient in matching_patients:
                    patient_id = patient.get('patient_id', '')
                    self.search_results.controls.append(
                        ft.ListTile(
                            title=ft.Text(f"{patient.get('name', '')} {patient.get('surname', '')}"),
                            subtitle=ft.Text(f"ID: {patient_id}, Date: {patient.get('date', '')}"),
                            on_click=lambda e, pid=patient_id: self.load_patient(e, pid)
                        )
                    )
                self.search_results.visible = True
            else:
                self.search_results.visible = False
                
            await e.page.update_async()
            
        except Exception as ex:
            await self.update_status(f"Error searching patients: {str(ex)}", e.page)
    
    async def load_patient(self, e, patient_id):
        """Load patient data when selected from search results"""
        if not patient_id or not self.database_path:
            return
            
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
                
                # Remember the original ID to avoid warning when saving the same patient
                self.original_patient_id = patient_id
                
                # Hide search results
                self.search_results.visible = False
                await e.page.update_async()
                await self.update_status(f"Loaded patient: {data.get('name', '')} {data.get('surname', '')}", e.page)
                
            except Exception as ex:
                await self.update_status(f"Error loading patient data: {str(ex)}", e.page)
        else:
            await self.update_status(f"Patient data file not found", e.page)
    
    async def save_patient_data(self, page):
        """Save current patient data to JSON file"""
        if not self.patient_data["patient_id"] or not self.database_path:
            return False
            
        patient_folder = os.path.join(self.database_path, self.patient_data["patient_id"])
        
        # Check if patient folder exists, create if it doesn't
        if not os.path.exists(patient_folder):
            os.makedirs(patient_folder)
            
        # Save patient data
        json_file = os.path.join(patient_folder, "patient_data.json")
        try:
            with open(json_file, 'w') as f:
                json.dump(self.patient_data, f, indent=4)
            return True
        except Exception as ex:
            await self.update_status(f"Error saving patient data: {str(ex)}", page)
            return False
    
    async def auto_save_task(self, page):
        """Periodically auto-save patient data"""
        while True:
            try:
                if self.patient_data["patient_id"] and self.database_path:
                    if await self.save_patient_data(page):
                        await self.update_status("Auto-saved patient data", page, temporary=True)
            except Exception as ex:
                await self.update_status(f"Auto-save error: {str(ex)}", page, temporary=True)
                
            await asyncio.sleep(4)  # Save every 4 seconds
    
    async def clear_form(self, e):
        """Clear all form fields"""
        self.patient_data = {
            "patient_id": "",
            "name": "",
            "surname": "",
            "date": datetime.date.today().strftime("%Y-%m-%d"),
            "initial_description": "",
            "scintigraphy": "",
            "fdg_pet": ""
        }
        
        self.name_field.value = ""
        self.surname_field.value = ""
        self.date_field.value = datetime.date.today().strftime("%Y-%m-%d")
        self.patient_id_field.value = ""
        self.initial_description.value = ""
        self.scintigraphy.value = ""
        self.fdg_pet.value = ""
        self.original_patient_id = None
        
        await e.page.update_async()
        await self.update_status("Form cleared", e.page)
    
    async def update_status(self, message, page, temporary=False):
        """Update status message at the bottom of the page"""
        self.status_text.value = message
        await page.update_async()
        
        if temporary:
            # Clear the status after a few seconds if it's a temporary message
            await asyncio.sleep(3)
            self.status_text.value = ""
            await page.update_async()


def main(page: ft.Page):
    app = PatientApp()
    return app.main(page)

ft.app(main)