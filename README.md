# lubelogger-fuelio-importer

Python script to import fuel records from [Fuelio](https://fuel.io/)'s Google Drive backups to [LubeLogger](https://github.com/hargata/lubelog).

## Requirements

- **LubeLogger**: v1.5.7 or later
- Python 3.12+ if using standalone method

# Usage

**Defaults:**

* The log level set in the execution args (`--log-level`) takes presedence over config.yml's `log_level`. If neither are set, it will default to `INFO`.
* If `config_dir` is unspecified, the default is to look for a directory named `config` in the script's current working direcory.  
  It can also be set by defining the `CONFIG_DIR` environment variable.

### Standalone

```sh
python3 main.py [-h|--help] [--dry-run] [--log-level {debug,info,warning,error,critical}] [config_dir]
```

### Docker

```sh
docker run --rm -v ./config:/app/config ghcr.io/tigattack/lubelogger-fuelio-importer:latest [--dry-run]
```

### Docker Compose

```sh
docker compose up [-d]
```

> [!TIP]
> You will need to download [docker-compose.yml](docker-compose.yml) to current directory before running.

# Getting Started

First, a couple of prerequisites:

* Fuelio must be configured to back up to Google Drive ([docs](https://www.fuel.io/faq_backup_help.html)).
* You must generate service credentials for the Google Drive API. Instructions can be found in the [Generate Google Drive API credentials](#generate-google-drive-api-credentials) section below.

Now you can complete the configuration for the importer:

1. Copy `config.example.yml` to `config.yml`, and open it in an editor.
2. Define your vehicle('s) IDs in Fuelio & LubeLogger.
3. Set your LubeLogger URL, username, and password.
4. Set your Google Drive folder ID (see instructions below).
5. Create your Google authentication credentials JSON (see instructions below) and move the file in place
6. Set your credentials filename and the relevant `auth_type` in the config.
7. Run the importer per the [Usage](#usage) section above.

## Retrieve your Fuelio vehicle ID

Fuelio vehicle IDs are chronological, i.e. the first vehicle you add to Fuelio is ID 1, the second is ID 2, and so on.

If you're unsure, download and extract the backup ZIP of each vehicle and inspect the CSV inside.

## Retrieve your Lubelogger vehicle ID

1. Open LubeLogger in a browser.
2. Navigate to the vehicle in question.
3. The vehicle ID will be in the URL like so: `https://lubelogger.domain.tld/Vehicle/Index?vehicleId=<vehicle ID here>`

## Retrieve your Google Drive Folder ID

1. Open Google Drive in a browser.
2. Navigate to the folder in which Fulio stores its backups.
3. The folder ID will be in the URL like so: `https://drive.google.com/drive/folders/<folder ID here>`

## Generate Google Drive API credentials

1. Go to APIs Console and make your own project.
2. Search for "Google Drive API", select the entry, and click "Enable".
3. Click Create Credentials at <https://console.cloud.google.com/apis/credentials>
4. Select "Service Account".
5. Enter an appropriate name.
6. Continue through steps 2 & 3.
7. Select the service account in the list.
8. Copy the service account's email address. We'll use this later.
9. Select the "Keys" tab and create a new key:
    1. Click "Add key"
    2. Select "Create new key"
    3. Select "JSON"
    4. Click "Create"
10. The service account key will be downloaded. Rename the file to "service_secrets.json"  and place it in your working directory.
11. Open Google Drive in a browser.
12. Navigate to the folder in which Fulio stores its backups.
13. Share the folder with the service account using email address you copied in step 8. The "Viewer" role is all it needs.

# Fuelio CSV Rant

I'd like to rant about the CSV files in Fuelio's backups.

What Fuelio have implemented in these files is a fundamentally broken CSV structure. TL;DR it should be multiple files or a proper hierarchical format, but instead it's a single file behaving as if it's multiple files hacked together.

1. Multiple sections in one file (`## Vehicle`, `## Log`, `## CostCategories`, etc.)
   - Each section has a completely different schema
   - There's no "standard" way to distinguish section markers from data rows
2. `csv.DictReader` treats the first row (`## Vehicle`) as the header for the entire file because... well, it should be
   - Result is all rows have their first column mapped to the `## Vehicle` key
   - All other columns in each row get shoved into a list under the `None` key
   - We're essentially parsing a multi-schema document as if it has one header row
3. Each section has its own column header row that we need to skip
4. The only way to identify fuel records is by knowing they're in the `## Log` section and/or Trying to parse the first column as a datetime (`YYYY-MM-DD HH:MM`) (less reliable).

As a result of all this, the parser is frustrating to work on, and feels convoluted and janky.

See [src/fuelio.py](src/fuelio.py) for implementation.
