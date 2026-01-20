"""File cleanup executor for tests."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from mcp_pytest.cleanup.tracker import FileTracker, TrackedFile

logger = logging.getLogger(__name__)


class FileCleaner:
    """
    Execute file cleanup operations.

    Features:
    - Safe deletion with error handling
    - Recursive directory removal
    - Dry-run mode for testing
    - Detailed logging
    """

    def __init__(
        self,
        tracker: FileTracker,
        dry_run: bool = False,
    ):
        """
        Initialize file cleaner.

        Args:
            tracker: FileTracker instance to get tracked files from.
            dry_run: If True, don't actually delete files (for testing).
        """
        self._tracker = tracker
        self._dry_run = dry_run

    def cleanup_test(
        self,
        test_name: str,
        force: bool = False,
    ) -> List[Path]:
        """
        Clean up files created by a specific test.

        Args:
            test_name: Name of the test to clean up.
            force: If True, ignore errors during deletion.

        Returns:
            List of paths that were successfully cleaned up.
        """
        tracked_files = self._tracker.get_tracked_files(test_name)

        if not tracked_files:
            logger.debug(f"No files to clean up for test '{test_name}'")
            return []

        cleaned: List[Path] = []

        # Sort by path depth (deepest first) to handle nested files/dirs
        sorted_files = sorted(tracked_files, key=lambda t: len(t.path.parts), reverse=True)

        for tracked in sorted_files:
            try:
                if self._delete_path(tracked.path, tracked.is_directory, force):
                    cleaned.append(tracked.path)
            except Exception as e:
                if not force:
                    logger.error(f"Failed to clean up {tracked.path}: {e}")
                else:
                    logger.warning(f"Failed to clean up {tracked.path}: {e}")

        # Clear tracking data for this test
        self._tracker.clear(test_name)

        logger.info(f"Cleaned up {len(cleaned)} file(s) for test '{test_name}'")
        return cleaned

    def cleanup_all(self, force: bool = False) -> List[Path]:
        """
        Clean up all tracked files across all tests.

        Args:
            force: If True, ignore errors during deletion.

        Returns:
            List of paths that were successfully cleaned up.
        """
        test_names = self._tracker.get_test_names()
        all_cleaned: List[Path] = []

        for test_name in test_names:
            cleaned = self.cleanup_test(test_name, force=force)
            all_cleaned.extend(cleaned)

        return all_cleaned

    def cleanup_paths(
        self,
        paths: List[Path | str],
        force: bool = False,
    ) -> List[Path]:
        """
        Clean up specific paths (not necessarily tracked).

        Args:
            paths: List of paths to clean up.
            force: If True, ignore errors during deletion.

        Returns:
            List of paths that were successfully cleaned up.
        """
        cleaned: List[Path] = []

        for path in paths:
            path = Path(path)
            is_dir = path.is_dir() if path.exists() else False

            try:
                if self._delete_path(path, is_dir, force):
                    cleaned.append(path)
            except Exception as e:
                if not force:
                    logger.error(f"Failed to clean up {path}: {e}")
                else:
                    logger.warning(f"Failed to clean up {path}: {e}")

        return cleaned

    def _delete_path(
        self,
        path: Path,
        is_directory: bool,
        force: bool,
    ) -> bool:
        """
        Delete a single path.

        Args:
            path: Path to delete.
            is_directory: Whether the path is a directory.
            force: If True, ignore errors.

        Returns:
            True if deletion was successful or path didn't exist.
        """
        if not path.exists():
            logger.debug(f"Path does not exist, skipping: {path}")
            return True

        if self._dry_run:
            logger.info(f"[DRY RUN] Would delete: {path}")
            return True

        try:
            if is_directory or path.is_dir():
                shutil.rmtree(path, ignore_errors=force)
                logger.debug(f"Removed directory: {path}")
            else:
                path.unlink(missing_ok=True)
                logger.debug(f"Removed file: {path}")

            return True

        except PermissionError as e:
            if force:
                logger.warning(f"Permission denied deleting {path}: {e}")
                return False
            raise

        except Exception as e:
            if force:
                logger.warning(f"Error deleting {path}: {e}")
                return False
            raise

    @property
    def dry_run(self) -> bool:
        """Check if in dry-run mode."""
        return self._dry_run

    @dry_run.setter
    def dry_run(self, value: bool) -> None:
        """Set dry-run mode."""
        self._dry_run = value
