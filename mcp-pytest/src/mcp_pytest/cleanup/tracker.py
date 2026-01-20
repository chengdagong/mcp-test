"""File tracking for test cleanup."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class TrackedFile:
    """Represents a tracked file or directory."""

    path: Path
    created_at: datetime
    test_name: str
    is_directory: bool = False

    def exists(self) -> bool:
        """Check if the file/directory still exists."""
        return self.path.exists()

    def __hash__(self) -> int:
        return hash((self.path, self.test_name))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TrackedFile):
            return False
        return self.path == other.path and self.test_name == other.test_name


class FileTracker:
    """
    Track files created during tests for cleanup.

    Features:
    - Manual file tracking via track()
    - Directory watching for new files
    - Test-scoped tracking
    - Thread-safe operations
    """

    def __init__(self):
        """Initialize file tracker."""
        self._tracked: Dict[str, List[TrackedFile]] = {}  # test_name -> files
        self._lock = threading.Lock()
        self._watched_directories: Dict[Path, _DirectoryWatch] = {}

    def track(
        self,
        path: Path | str,
        test_name: str,
    ) -> TrackedFile:
        """
        Manually track a file or directory for cleanup.

        Args:
            path: Path to the file or directory.
            test_name: Name of the test that created this file.

        Returns:
            TrackedFile instance.
        """
        path = Path(path).resolve()

        tracked = TrackedFile(
            path=path,
            created_at=datetime.now(),
            test_name=test_name,
            is_directory=path.is_dir() if path.exists() else False,
        )

        with self._lock:
            if test_name not in self._tracked:
                self._tracked[test_name] = []

            # Avoid duplicates
            existing = [t for t in self._tracked[test_name] if t.path == path]
            if not existing:
                self._tracked[test_name].append(tracked)
                logger.debug(f"Tracking {path} for test '{test_name}'")

        return tracked

    def track_multiple(
        self,
        paths: List[Path | str],
        test_name: str,
    ) -> List[TrackedFile]:
        """
        Track multiple files/directories.

        Args:
            paths: List of paths to track.
            test_name: Name of the test.

        Returns:
            List of TrackedFile instances.
        """
        return [self.track(p, test_name) for p in paths]

    def start_watching(
        self,
        directory: Path | str,
        test_name: str,
    ) -> None:
        """
        Start watching a directory for new files.

        Any new files created in the directory will be automatically tracked.

        Args:
            directory: Directory to watch.
            test_name: Name of the test.
        """
        directory = Path(directory).resolve()

        if not directory.is_dir():
            logger.warning(f"Cannot watch non-directory: {directory}")
            return

        with self._lock:
            if directory not in self._watched_directories:
                self._watched_directories[directory] = _DirectoryWatch(
                    directory=directory,
                    test_name=test_name,
                    initial_contents=set(directory.iterdir()) if directory.exists() else set(),
                )
                logger.debug(f"Started watching {directory} for test '{test_name}'")

    def stop_watching(
        self,
        directory: Path | str,
    ) -> List[TrackedFile]:
        """
        Stop watching a directory and track any new files found.

        Args:
            directory: Directory to stop watching.

        Returns:
            List of newly detected files that were tracked.
        """
        directory = Path(directory).resolve()

        with self._lock:
            if directory not in self._watched_directories:
                return []

            watch = self._watched_directories.pop(directory)

        # Find new files
        new_files: List[TrackedFile] = []

        if directory.exists():
            current_contents = set(directory.iterdir())
            new_paths = current_contents - watch.initial_contents

            for path in new_paths:
                tracked = self.track(path, watch.test_name)
                new_files.append(tracked)

        logger.debug(f"Stopped watching {directory}, found {len(new_files)} new files")
        return new_files

    def stop_all_watching(self) -> List[TrackedFile]:
        """
        Stop watching all directories.

        Returns:
            List of all newly detected files.
        """
        directories = list(self._watched_directories.keys())
        all_new: List[TrackedFile] = []

        for directory in directories:
            new_files = self.stop_watching(directory)
            all_new.extend(new_files)

        return all_new

    def get_tracked_files(self, test_name: str) -> List[TrackedFile]:
        """
        Get all tracked files for a test.

        Args:
            test_name: Name of the test.

        Returns:
            List of tracked files (copy).
        """
        with self._lock:
            return list(self._tracked.get(test_name, []))

    def get_all_tracked_files(self) -> List[TrackedFile]:
        """
        Get all tracked files across all tests.

        Returns:
            List of all tracked files.
        """
        with self._lock:
            all_files: List[TrackedFile] = []
            for files in self._tracked.values():
                all_files.extend(files)
            return all_files

    def get_test_names(self) -> List[str]:
        """Get list of all test names with tracked files."""
        with self._lock:
            return list(self._tracked.keys())

    def clear(self, test_name: Optional[str] = None) -> None:
        """
        Clear tracking data.

        Args:
            test_name: Specific test to clear. If None, clears all.
        """
        with self._lock:
            if test_name is not None:
                self._tracked.pop(test_name, None)
            else:
                self._tracked.clear()
                self._watched_directories.clear()

    def file_count(self, test_name: Optional[str] = None) -> int:
        """
        Get count of tracked files.

        Args:
            test_name: Specific test to count. If None, counts all.

        Returns:
            Number of tracked files.
        """
        with self._lock:
            if test_name is not None:
                return len(self._tracked.get(test_name, []))
            return sum(len(files) for files in self._tracked.values())


@dataclass
class _DirectoryWatch:
    """Internal class for directory watching state."""

    directory: Path
    test_name: str
    initial_contents: Set[Path] = field(default_factory=set)
