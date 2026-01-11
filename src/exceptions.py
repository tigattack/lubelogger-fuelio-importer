"""Custom exceptions"""


class LubeloggerFuelioError(Exception):
    """Base exception for all Lubelogger-Fuelio sync errors"""

    pass


class ConfigError(LubeloggerFuelioError):
    """Configuration-related errors"""

    pass


class FuelioDataError(LubeloggerFuelioError):
    """Fuelio data processing errors"""

    pass


class LubeloggerAPIError(LubeloggerFuelioError):
    """Lubelogger API errors"""

    pass


class GDriveError(LubeloggerFuelioError):
    """Google Drive API errors"""

    pass


class SyncError(LubeloggerFuelioError):
    """Sync operation errors"""

    pass
