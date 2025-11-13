"""
Configuration Manager
=====================
Centralized user settings and preferences management for PRISMA.

Handles:
- Workspace directory selection
- GSAS-II installation path
- Update check preferences
- GUI settings and preferences

Settings are stored in ~/.prisma/config.json
"""

import json
import os
from pathlib import Path
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    'workspace_path': None,  # Will be set on first launch
    'gsas_path': None,  # GSAS-II installation directory
    'check_updates': True,  # Enable auto-update checks
    'last_update_check': None,  # ISO timestamp of last update check
    'show_update_notifications': True,  # Show update notification dialogs
    'window_geometry': None,  # Main window position/size (saved as dict)
    'recent_recipes': [],  # List of recently opened recipe files
    'max_recent_recipes': 10,  # Maximum number of recent recipes to track
    'theme': 'default',  # GUI theme (future use)
    'first_launch': True,  # Flag for first-time setup wizard
}


class ConfigManager:
    """
    Manages user configuration and preferences.

    Configuration is stored in JSON format at ~/.prisma/config.json
    Provides thread-safe access to settings.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Custom path to config file (default: ~/.prisma/config.json)
        """
        if config_path is None:
            config_dir = Path.home() / '.prisma'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / 'config.json'

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Dictionary of configuration settings

        If file doesn't exist or is invalid, returns default configuration.
        """
        if not self.config_path.exists():
            logger.info(f"No config file found, creating default at {self.config_path}")
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r') as f:
                loaded_config = json.load(f)

            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(loaded_config)

            logger.info(f"Loaded configuration from {self.config_path}")
            return config

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading config file: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()

    def save_config(self) -> bool:
        """
        Save current configuration to file.

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write config with pretty formatting
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)

            logger.debug(f"Configuration saved to {self.config_path}")
            return True

        except IOError as e:
            logger.error(f"Error saving config file: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> bool:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: New value
            save: Automatically save config to file (default: True)

        Returns:
            True if successful
        """
        self.config[key] = value

        if save:
            return self.save_config()
        return True

    def get_workspace_path(self) -> Optional[str]:
        """
        Get configured workspace directory path.

        Returns:
            Workspace path or None if not configured
        """
        return self.config.get('workspace_path')

    def set_workspace_path(self, path: str, save: bool = True) -> bool:
        """
        Set workspace directory path.

        Args:
            path: Absolute path to workspace directory
            save: Automatically save config (default: True)

        Returns:
            True if successful
        """
        # Convert to absolute path
        abs_path = os.path.abspath(path)

        self.config['workspace_path'] = abs_path
        logger.info(f"Workspace set to: {abs_path}")

        if save:
            return self.save_config()
        return True

    def get_gsas_path(self) -> Optional[str]:
        """
        Get GSAS-II installation directory path.

        Returns:
            GSAS-II path or None if not configured
        """
        return self.config.get('gsas_path')

    def set_gsas_path(self, path: str, save: bool = True) -> bool:
        """
        Set GSAS-II installation directory.

        Args:
            path: Absolute path to GSAS-II directory
            save: Automatically save config (default: True)

        Returns:
            True if successful
        """
        abs_path = os.path.abspath(path)

        self.config['gsas_path'] = abs_path
        logger.info(f"GSAS-II path set to: {abs_path}")

        if save:
            return self.save_config()
        return True

    def is_first_launch(self) -> bool:
        """
        Check if this is the first time PRISMA is being launched.

        Returns:
            True if first launch
        """
        return self.config.get('first_launch', True)

    def set_first_launch_complete(self, save: bool = True) -> bool:
        """
        Mark first-time setup as complete.

        Args:
            save: Automatically save config (default: True)

        Returns:
            True if successful
        """
        return self.set('first_launch', False, save=save)

    def add_recent_recipe(self, recipe_path: str, save: bool = True) -> bool:
        """
        Add recipe to recent files list.

        Args:
            recipe_path: Absolute path to recipe file
            save: Automatically save config (default: True)

        Returns:
            True if successful
        """
        recent = self.config.get('recent_recipes', [])

        # Remove if already in list
        if recipe_path in recent:
            recent.remove(recipe_path)

        # Add to front of list
        recent.insert(0, recipe_path)

        # Trim to max length
        max_recent = self.config.get('max_recent_recipes', 10)
        self.config['recent_recipes'] = recent[:max_recent]

        if save:
            return self.save_config()
        return True

    def get_recent_recipes(self) -> list:
        """
        Get list of recently opened recipe files.

        Returns:
            List of recipe file paths (most recent first)
        """
        recent = self.config.get('recent_recipes', [])

        # Filter out files that no longer exist
        existing = [path for path in recent if os.path.exists(path)]

        # Update config if any were removed
        if len(existing) != len(recent):
            self.config['recent_recipes'] = existing
            self.save_config()

        return existing

    def should_check_updates(self) -> bool:
        """
        Check if auto-update checking is enabled.

        Returns:
            True if updates should be checked
        """
        return self.config.get('check_updates', True)

    def set_check_updates(self, enabled: bool, save: bool = True) -> bool:
        """
        Enable or disable auto-update checking.

        Args:
            enabled: True to enable update checks
            save: Automatically save config (default: True)

        Returns:
            True if successful
        """
        return self.set('check_updates', enabled, save=save)

    def get_window_geometry(self) -> Optional[Dict[str, int]]:
        """
        Get saved main window geometry.

        Returns:
            Dictionary with 'x', 'y', 'width', 'height' or None
        """
        return self.config.get('window_geometry')

    def set_window_geometry(self, x: int, y: int, width: int, height: int, save: bool = True) -> bool:
        """
        Save main window geometry.

        Args:
            x: Window x position
            y: Window y position
            width: Window width
            height: Window height
            save: Automatically save config (default: True)

        Returns:
            True if successful
        """
        geometry = {
            'x': x,
            'y': y,
            'width': width,
            'height': height
        }
        return self.set('window_geometry', geometry, save=save)

    def reset_to_defaults(self, save: bool = True) -> bool:
        """
        Reset configuration to default values.

        Args:
            save: Automatically save config (default: True)

        Returns:
            True if successful
        """
        self.config = DEFAULT_CONFIG.copy()
        logger.warning("Configuration reset to defaults")

        if save:
            return self.save_config()
        return True


# Singleton instance for global access
_config_manager_instance = None


def get_config_manager() -> ConfigManager:
    """
    Get global configuration manager instance (singleton).

    Returns:
        ConfigManager instance
    """
    global _config_manager_instance

    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()

    return _config_manager_instance


if __name__ == "__main__":
    # Test the config manager
    logging.basicConfig(level=logging.INFO)

    config = ConfigManager()

    print("\n" + "="*60)
    print("PRISMA Configuration Manager Test")
    print("="*60)

    print(f"\nConfig file location: {config.config_path}")
    print(f"First launch: {config.is_first_launch()}")
    print(f"Workspace path: {config.get_workspace_path()}")
    print(f"GSAS-II path: {config.get_gsas_path()}")
    print(f"Check for updates: {config.should_check_updates()}")
    print(f"Recent recipes: {config.get_recent_recipes()}")

    print("\n" + "="*60)
