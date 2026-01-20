"""YAML configuration loader for MCP tests."""

import logging
from pathlib import Path
from typing import Optional

import yaml

from mcp_pytest.config.models import MCPTestConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage MCP test configurations from YAML files."""

    DEFAULT_CONFIG_NAMES = [
        "mcp_servers.yaml",
        "mcp_servers.yml",
        ".mcp_servers.yaml",
        ".mcp_servers.yml",
        "mcp-servers.yaml",
        "mcp-servers.yml",
    ]

    @classmethod
    def load(
        cls,
        config_path: Optional[str | Path] = None,
        root_dir: Optional[Path] = None,
    ) -> MCPTestConfig:
        """
        Load configuration from YAML file.

        Args:
            config_path: Explicit path to config file. If None, searches for default files.
            root_dir: Root directory to search for config files. Defaults to current directory.

        Returns:
            MCPTestConfig instance with loaded configuration.

        Raises:
            FileNotFoundError: If explicit config_path is given but doesn't exist.
        """
        if root_dir is None:
            root_dir = Path.cwd()

        if config_path is not None:
            path = Path(config_path)
            if not path.is_absolute():
                path = root_dir / path
            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {path}")
            return cls._load_from_file(path)

        # Search for default config files
        found_path = cls.find_config_file(root_dir)
        if found_path:
            return cls._load_from_file(found_path)

        # Return default config if no file found
        logger.info("No MCP configuration file found, using defaults")
        return MCPTestConfig()

    @classmethod
    def find_config_file(cls, start_dir: Path) -> Optional[Path]:
        """
        Search for config file in directory hierarchy.

        Searches in start_dir and parent directories up to root.

        Args:
            start_dir: Directory to start searching from.

        Returns:
            Path to found config file, or None if not found.
        """
        current = start_dir.resolve()

        while True:
            for name in cls.DEFAULT_CONFIG_NAMES:
                candidate = current / name
                if candidate.exists() and candidate.is_file():
                    logger.debug(f"Found MCP config file: {candidate}")
                    return candidate

            # Move to parent directory
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent

        return None

    @classmethod
    def _load_from_file(cls, path: Path) -> MCPTestConfig:
        """
        Load configuration from a specific file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            MCPTestConfig instance.
        """
        logger.info(f"Loading MCP configuration from: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            data = {}

        return MCPTestConfig.model_validate(data)

    @classmethod
    def merge_configs(cls, base: MCPTestConfig, override: MCPTestConfig) -> MCPTestConfig:
        """
        Merge two configurations, with override taking precedence.

        Args:
            base: Base configuration.
            override: Configuration to override base with.

        Returns:
            Merged MCPTestConfig instance.
        """
        base_dict = base.model_dump()
        override_dict = override.model_dump(exclude_unset=True)

        # Merge servers by name
        base_servers = {s["name"]: s for s in base_dict.get("servers", [])}
        override_servers = {s["name"]: s for s in override_dict.get("servers", [])}
        base_servers.update(override_servers)

        merged_dict = {**base_dict, **override_dict}
        merged_dict["servers"] = list(base_servers.values())

        return MCPTestConfig.model_validate(merged_dict)
