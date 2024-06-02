# lubelogger-fuelio-importer

Python script to import fuel fill-ups from Fuelio's Google Drive backups to [Lubelogger](https://github.com/hargata/lubelog).

# Usage

Standalone:

```sh
python3 main.py [--dry-run]
```

Docker:

```sh
docker run --rm -v config.yml:/app/config.yml ghcr.io/tigattack/lubelogger-fuelio-importer:latest [--dry-run]
```

# Getting Started

First, a couple of prerequisites:

* Fuelio must be configured to back up to Google Drive ([docs](https://www.fuel.io/faq_backup_help.html)).
* You must generate service or client credentials for the Google Drive API. Client credentials require interactive (browser) authentication, while service accounts do not. Pick the most appropriate option for your case.

The basic process is as follows, and you can review each section below as needed:

1. Copy `config.example.yml` to `config.yml`, and open it in an editor.
2. Discover & set your vehicle ID for Fuelio & Lubelogger.
3. Set your Lubelogger domain, username, and password.
4. Create your Google authentication credentials JSON, move the file in place, and set the relevant `auth_type`.

## Retrieve your Fuelio vehicle ID

Fuelio vehicle IDs are chronological, i.e. the first vehicle you add to Fuelio is ID 1, the second is ID 2, and so on.

If you're unsure, download and extract the backup ZIP of each vehicle and inspect the CSV inside.

## Retrieve your Lubelogger vehicle ID

1. Open Lubelogger in a browser.
2. Navigate to the vehicle in question.
3. The vehicle ID will be in the URL like so: `https://lubelogger.domain.tld/Vehicle/Index?vehicleId=<vehicle ID here>`

## Retrieve your Google Drive Folder ID

1. Open Google Drive in a browser.
2. Navigate to the folder in which Fulio stores its backups.
3. The folder ID will be in the URL like so: `https://drive.google.com/drive/folders/<folder ID here>`

## Generate your Google Drive API credentials

1. Go to APIs Console and make your own project.
2. Search for "Google Drive API", select the entry, and click "Enable".
3. Based on the authentication type you've chosen, follow the relevant set of instructions below.

### Client Credentials

1. Click Create Credentials at https://console.cloud.google.com/apis/credentials
2. Select "OAuth client ID".
3. Now, the product name and consent screen need to be set -> click "Configure consent screen" and follow the instructions. Once finished:
    1. Select "Application type" to be Web application.
    2. Enter an appropriate name.
    3. Input http://localhost:8080/ for "Authorized redirect URIs".
    4. Click "Create".
4. Click "Download JSON" on the right side of Client ID to download `client_secret_<really long ID>.json`.
5. The downloaded file has all authentication information of your application. Rename the file to “client_secrets.json” and place it in your working directory.

### Service Account Credentials

1. Click Create Credentials at https://console.cloud.google.com/apis/credentials
2. Select "Service Account".
3. Enter an appropriate name.
4. Continue through steps 2 & 3.
5. Select the service account in the list.
6. Copy the service account's email address. We'll use this later.
7. Select the "Keys" tab and create a new key:
    1. Click "Add key"
    2. Select "Create new key"
    3. Select "JSON"
    4. Click "Create"
8. The service account key will be downloaded. Rename the file to "service_secrets.json"  and place it in your working directory.
9. Open Google Drive in a browser.
10. Navigate to the folder in which Fulio stores its backups.
11. Share the folder with the service account using email address you copied in step 6. The "Viewer" role is all it needs.
