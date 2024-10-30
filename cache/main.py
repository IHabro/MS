import os
import pickle
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

# Scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER = '1-Ed9kaP0fJdJq0rT0-buw9gw3hcm_80y'  # Default folder ID
DOWNLOAD = r'C:\Users\vohab\source\repos\School\Ing\MS\GoogleDrive\Download'  # Local download folder

# Cached items list
cached_items = []
last_known_files = []  # To store the last known folder contents
copy_cut_item = None  # To store the item being copied or cut
operation_mode = None  # 'copy' or 'cut'

def authenticate_google_drive():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

class DriveBrowserApp:
    def __init__(self, root, service):
        self.root = root
        self.service = service
        self.current_folder_id = FOLDER
        self.root.title("Google Drive Browser")
        self.root.geometry("600x500")
        self.is_logged_in = True  # Track login state

        # Service section with buttons
        service_frame = tk.Frame(self.root)
        service_frame.pack(fill=tk.X, padx=10, pady=5)

        # Upload, Download, Cache, and Remove Cache Buttons
        self.create_service_buttons(service_frame)

        # Status Label
        self.status_label = tk.Label(self.root, text="Status: Online", anchor='e')
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

        # Treeview for displaying files and folders
        self.tree = ttk.Treeview(self.root, selectmode="extended")
        self.tree.heading("#0", text="Google Drive", anchor='w')
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Bind double-click event to enter folders
        self.tree.bind("<Double-1>", self.on_item_double_click)

        # Load the default folder contents
        self.load_folder_contents(FOLDER)

    def create_service_buttons(self, parent):
        # Frame for main service buttons
        service_frame = tk.Frame(parent)
        service_frame.pack(fill=tk.X, padx=10, pady=5)

        # Create main service buttons
        upload_button = tk.Button(service_frame, text="Upload", command=self.upload_file)
        upload_button.pack(side=tk.LEFT, padx=5)

        download_button = tk.Button(service_frame, text="Download", command=self.download_files)
        download_button.pack(side=tk.LEFT, padx=5)

        cache_button = tk.Button(service_frame, text="Cache Selected", command=self.cache_selected)
        cache_button.pack(side=tk.LEFT, padx=5)

        remove_cache_button = tk.Button(service_frame, text="Remove Cache", command=self.remove_cached)
        remove_cache_button.pack(side=tk.LEFT, padx=5)

        logout_button = tk.Button(service_frame, text="Logout", command=self.logout)
        logout_button.pack(side=tk.LEFT, padx=5)

        login_button = tk.Button(service_frame, text="Login", command=self.login)
        login_button.pack(side=tk.LEFT, padx=5)

        end_app_button = tk.Button(service_frame, text="End App", command=self.end_app)
        end_app_button.pack(side=tk.LEFT, padx=5)

        # New frame for file operations
        operation_frame = tk.Frame(parent)
        operation_frame.pack(fill=tk.X, padx=10, pady=5)

        # Create buttons for file operations
        copy_button = tk.Button(operation_frame, text="Copy", command=self.copy_item)
        copy_button.pack(side=tk.LEFT, padx=5)

        cut_button = tk.Button(operation_frame, text="Cut", command=self.cut_item)
        cut_button.pack(side=tk.LEFT, padx=5)

        paste_button = tk.Button(operation_frame, text="Paste", command=self.paste_item)
        paste_button.pack(side=tk.LEFT, padx=5)

        rename_button = tk.Button(operation_frame, text="Rename", command=self.rename_item)
        rename_button.pack(side=tk.LEFT, padx=5)

        delete_button = tk.Button(operation_frame, text="Delete", command=self.delete_item)
        delete_button.pack(side=tk.LEFT, padx=5)

    def load_folder_contents(self, folder_id):
        # Clear the tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.is_logged_in:
            # If offline, display last known files or cached items
            for item in last_known_files:
                self.tree.insert('', 'end', item['id'], text=item['name'], tags=('file',))
            return

        # Add '.' and '..' entries
        self.tree.insert('', 'end', '.', text='.', tags=('folder',))
        if folder_id != FOLDER:  # Allow going up only if not at the root
            self.tree.insert('', 'end', '..', text='..', tags=('folder',))

        # Get contents of the folder
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name, mimeType)"
            ).execute()
            files = results.get('files', [])

            # Update last known files
            last_known_files.clear()
            last_known_files.extend(files)

            for file in files:
                # Display folders and files with icons
                if file['mimeType'] == 'application/vnd.google-apps.folder':
                    self.tree.insert('', 'end', file['id'], text=file['name'], tags=('folder',))
                else:
                    self.tree.insert('', 'end', file['id'], text=file['name'], tags=('file',))
        except HttpError as error:
            messagebox.showerror("Error", f"An error occurred: {error}")

    def on_item_double_click(self, event):
        # Get the selected item
        selected_item = self.tree.selection()[0]
        item_tags = self.tree.item(selected_item, 'tags')

        if selected_item == '.':
            # Do nothing for the current directory
            return
        elif selected_item == '..':
            # Navigate to the parent folder
            if self.current_folder_id != FOLDER:
                # Go back to the parent folder (retrieve parent ID)
                parent_folder = self.get_parent_folder(self.current_folder_id)
                if parent_folder:
                    self.current_folder_id = parent_folder
                    self.load_folder_contents(self.current_folder_id)
            return
        elif 'folder' in item_tags:
            # If it's a folder, navigate into it
            self.current_folder_id = selected_item
            self.load_folder_contents(self.current_folder_id)
        elif 'file' in item_tags:
            # For files, prompt user with a message
            messagebox.showinfo("Info", "Selected item is a file.")

    def get_parent_folder(self, folder_id):
        """Get the parent folder ID."""
        try:
            file = self.service.files().get(fileId=folder_id, fields="parents").execute()
            parents = file.get('parents', [])
            return parents[0] if parents else None  # Return the first parent ID
        except HttpError as error:
            messagebox.showerror("Error", f"An error occurred while retrieving the parent folder: {error}")
            return None

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            print("No file selected.")
            return

        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [self.current_folder_id]  # Upload to current folder
        }
        media = MediaFileUpload(file_path, resumable=True)
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"File uploaded: {file.get('id')}")
            self.load_folder_contents(self.current_folder_id)  # Refresh view
        except HttpError as error:
            messagebox.showerror("Error", f"An error occurred: {error}")

    def download_files(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Download", "No files selected for download.")
            return

        for item_id in selected_items:
            item_tags = self.tree.item(item_id, 'tags')
            if 'file' in item_tags:
                self.download_file(item_id)

    def download_file(self, file_id):
        try:
            file = self.service.files().get(fileId=file_id).execute()
            file_name = file.get('name')
            file_path = os.path.join(DOWNLOAD, file_name)

            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%.")

            # Save the file to local storage
            with open(file_path, 'wb') as f:
                f.write(fh.getvalue())
            messagebox.showinfo("Download", f"File downloaded: {file_name}")

        except HttpError as error:
            messagebox.showerror("Error", f"An error occurred: {error}")

    def cache_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Cache", "No items selected for caching.")
            return

        for item_id in selected_items:
            item_name = self.tree.item(item_id, 'text')
            cached_items.append({'id': item_id, 'name': item_name})

        messagebox.showinfo("Cache", "Selected items cached successfully.")

    def remove_cached(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Remove Cache", "No cached items selected for removal.")
            return

        for item_id in selected_items:
            cached_items[:] = [item for item in cached_items if item['id'] != item_id]

        messagebox.showinfo("Remove Cache", "Cached items removed successfully.")

    def copy_item(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Copy", "No items selected to copy.")
            return
        global copy_cut_item, operation_mode
        copy_cut_item = selected_items[0]
        operation_mode = 'copy'
        messagebox.showinfo("Copy", f"Item {self.tree.item(copy_cut_item, 'text')} copied.")

    def cut_item(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Cut", "No items selected to cut.")
            return
        global copy_cut_item, operation_mode
        copy_cut_item = selected_items[0]
        operation_mode = 'cut'
        messagebox.showinfo("Cut", f"Item {self.tree.item(copy_cut_item, 'text')} cut.")

    def paste_item(self):
        global copy_cut_item, operation_mode
        if not copy_cut_item:
            messagebox.showinfo("Paste", "No item to paste.")
            return

        try:
            file_metadata = {
                'name': self.tree.item(copy_cut_item, 'text'),
                'parents': [self.current_folder_id]  # Target folder ID
            }

            if operation_mode == 'copy':
                # Create a copy
                self.service.files().copy(fileId=copy_cut_item, body=file_metadata).execute()
                messagebox.showinfo("Paste", "Item copied successfully.")
            elif operation_mode == 'cut':
                # Move the item
                self.service.files().update(fileId=copy_cut_item, addParents=self.current_folder_id,
                                             removeParents=self.get_parent_folder(copy_cut_item)).execute()
                messagebox.showinfo("Paste", "Item moved successfully.")

            self.load_folder_contents(self.current_folder_id)  # Refresh view
            copy_cut_item = None  # Clear the stored item after pasting
            operation_mode = None  # Clear the operation mode

        except HttpError as error:
            messagebox.showerror("Error", f"An error occurred: {error}")

    def rename_item(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Rename", "No item selected to rename.")
            return

        item_id = selected_items[0]
        current_name = self.tree.item(item_id, 'text')
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=current_name)

        if new_name:
            try:
                self.service.files().update(fileId=item_id, body={'name': new_name}).execute()
                messagebox.showinfo("Rename", "Item renamed successfully.")
                self.load_folder_contents(self.current_folder_id)  # Refresh view
            except HttpError as error:
                messagebox.showerror("Error", f"An error occurred: {error}")

    def delete_item(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Delete", "No item selected for deletion.")
            return

        for item_id in selected_items:
            try:
                self.service.files().delete(fileId=item_id).execute()
                messagebox.showinfo("Delete", "Item deleted successfully.")
            except HttpError as error:
                messagebox.showerror("Error", f"An error occurred: {error}")

        self.load_folder_contents(self.current_folder_id)  # Refresh view after deletion

    def logout(self):
        self.is_logged_in = False
        self.status_label.config(text="Status: Offline")  # Update status label
        self.load_folder_contents("")  # Clear the view

    def login(self):
        self.is_logged_in = True
        self.status_label.config(text="Status: Online")  # Update status label
        self.load_folder_contents(FOLDER)  # Load default folder

    def end_app(self):
        self.root.quit()

def main():
    root = tk.Tk()
    service = authenticate_google_drive()
    app = DriveBrowserApp(root, service)
    root.mainloop()

if __name__ == '__main__':
    main()
