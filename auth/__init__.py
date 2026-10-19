"""
Módulo de autenticación y control de licencias remotas.
"""
from .license_manager import LicenseManager
from .cloud_auth import CloudAuthManager

__all__ = ["LicenseManager", "CloudAuthManager"]
