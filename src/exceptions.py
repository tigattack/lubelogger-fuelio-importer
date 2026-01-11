"""Custom exceptions"""


class LubeLoggerFuelioError(Exception):
    """Base exception for all LubeLogger-Fuelio sync errors"""

    pass


class ConfigError(LubeLoggerFuelioError):
    """Configuration-related errors"""

    pass


class FuelioDataError(LubeLoggerFuelioError):
    """Fuelio data processing errors"""

    pass


class LubeLoggerAPIError(LubeLoggerFuelioError):
    """LubeLogger API errors"""

    pass


class GDriveError(LubeLoggerFuelioError):
    """Google Drive API errors"""

    pass


class SyncError(LubeLoggerFuelioError):
    """Sync operation errors"""

    pass
