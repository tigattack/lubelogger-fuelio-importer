# lubelogger-fuelio-importer

Python script to import fuel records from [Fuelio](https://fuel.io/)'s Google Drive backups to [LubeLogger](https://github.com/hargata/lubelog).

## Requirements

- **LubeLogger**: v1.5.7 or later
- Python 3.12+ if using standalone method

## Usage

```sh
❯ python3 cli.py -h
usage: cli.py [-h] [--dry-run] [--clobber] [--log-level {debug,info,warning,error,critical}]
               [config_dir]

Import Fuelio fuel records into LubeLogger

positional arguments:
  config_dir            Config directory

options:
  -h, --help            show this help message and exit
  --dry-run             Perform a dry run without making any changes
  --clobber             Override LubeLogger fuel records with Fuelio data when conflicts are found (based on matching date and mileage)
  --log-level {debug,info,warning,error,critical}
                        Log level to use (overrides config file)
```

**Defaults:**

* The log level set in the execution args (`--log-level`) takes presedence over config.yml's `log_level`. If neither are set, it will default to `INFO`.
* If `config_dir` is unspecified, the default is to look for a directory named `config` in the script's current working direcory.  
  It can also be set by defining the `CONFIG_DIR` environment variable.

### Clobber Mode

By default, when the importer finds a fuel record in LubeLogger with the same date and mileage as a record from Fuelio but with different attributes (e.g., different cost, fuel amount, or notes), it will log a warning and skip the record.

The `--clobber` flag enables Fuelio to be used as the source of truth: when a conflict is detected with different attributes, the LubeLogger record will be updated with the data from Fuelio.

**Use cases:**
- You've manually edited fuel records in LubeLogger and want to restore them from Fuelio backups
- You've made corrections in Fuelio and want to sync those changes to LubeLogger
- You want to ensure LubeLogger always matches your Fuelio data

**Example:**
```sh
python3 cli.py --clobber
```

When used with `--dry-run`, the importer will show what would be updated without making any changes:
```sh
python3 cli.py --dry-run --clobber
```

### Standalone

- Clone repository
- [Optional] Checkout tag
- Change to `src` directory
- Run `python3 cli.py <args>`

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

### Example

```sh
❯ python3 cli.py
2026-01-12 01:21:36,585 - INFO - Starting Fuelio to LubeLogger sync
2026-01-12 01:21:36,590 - INFO - SYNCING LUBELOGGER VEHICLE 2 ← FUELIO VEHICLE 5
2026-01-12 01:21:36,679 - INFO - Found LubeLogger vehicle: 1997 BMW Z3 (R123ABC)
2026-01-12 01:21:37,889 - INFO - Loaded 10 fuel records from Fuelio backup
2026-01-12 01:21:37,904 - INFO - Found 10 fuel records in LubeLogger
2026-01-12 01:21:37,904 - INFO - Nothing to add, LubeLogger fuel logs are up to date!
2026-01-12 01:21:37,905 - INFO - SYNCING LUBELOGGER VEHICLE 4 ← FUELIO VEHICLE 6
2026-01-12 01:21:37,951 - INFO - Found LubeLogger vehicle: 2008 BMW 335i (AB12CDE)
2026-01-12 01:21:39,079 - INFO - Loaded 54 fuel records from Fuelio backup
2026-01-12 01:21:39,097 - INFO - Found 53 fuel records in LubeLogger
2026-01-12 01:21:39,100 - INFO - Adding fuel record from 2026-01-04
2026-01-12 01:21:39,159 - INFO - Added 1 fuel record(s)
2026-01-12 01:21:39,178 - INFO - Sync complete
```

## Getting Started

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

### Retrieve your Fuelio vehicle ID

Fuelio vehicle IDs are chronological, i.e. the first vehicle you add to Fuelio is ID 1, the second is ID 2, and so on.

You can list your Fuelio vehicles with the `--list-fuelio-vehicles` option:

```sh
❯ python3 cli.py --list-fuelio-vehicles
2026-07-03 23:01:30,903 - INFO - Loaded 7 vehicles from Fuelio backup
Fuelio Vehicle: Yamaha YBR125, ID: 7
Fuelio Vehicle: BMW 335i, ID: 6
Fuelio Vehicle: BMW Z3, ID: 5
Fuelio Vehicle: Audi A4, ID: 4
Fuelio Vehicle: Volkswagen Bora, ID: 3
Fuelio Vehicle: Volkswagen Golf, ID: 2
Fuelio Vehicle: Renault Clio, ID: 1
```

Alternatively, download and extract the backup ZIP of each vehicle and inspect the CSV inside.

### Retrieve your LubeLogger vehicle ID

You can list your fuelio vehicles with the `--list-lubelogger-vehicles` option:

```sh
❯ python3 cli.py --list-lubelogger-vehicles
LubeLogger Vehicle: Audi A4, ID: 1
LubeLogger Vehicle: BMW Z3, ID: 2
LubeLogger Vehicle: BMW 335i, ID: 4
LubeLogger Vehicle: Volvo Test, ID: 5
LubeLogger Vehicle: Yamaha YBR125, ID: 6
```

Alternatively, you can browse to the vehicle in LubeLogger and extract the ID from the URL:

1. Open LubeLogger in a browser.
2. Navigate to the vehicle in question.
3. The vehicle ID will be in the URL like so: `https://lubelogger.domain.tld/Vehicle/Index?vehicleId=<vehicle ID here>`

### Retrieve your Google Drive Folder ID

1. Open Google Drive in a browser.
2. Navigate to the folder in which Fulio stores its backups.
3. The folder ID will be in the URL like so: `https://drive.google.com/drive/folders/<folder ID here>`

### Generate Google Drive API credentials

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
10. The service account key will be downloaded. Rename the file to "service_secrets.json" and place it alongside `config.yml` (or elsewhere; path can be configured).
11. Open Google Drive in a browser.
12. Navigate to the folder in which Fulio stores its backups.
13. Share the folder with the service account using email address you copied in step 8. The "Viewer" role is all it needs.

---

## Fuelio CSV Rant

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

See [src/fuelio.py](src/fuelio.py) and [src/flio_models.py](src/flio_models.py) for implementation.
