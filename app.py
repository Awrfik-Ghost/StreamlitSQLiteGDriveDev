from google.oauth2 import service_account
from googleapiclient.discovery import build

# Authenticate using the service account
creds = service_account.Credentials.from_service_account_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/drive.file']
)

# Build the Drive service
service = build('drive', 'v3', credentials=creds)

# Try to list files
results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
items = results.get('files', [])
if not items:
    print("No files found.")
else:
    print("Files:")
    for item in items:
        print(f"{item['name']} ({item['id']})")
