from __future__ import annotations

import pathlib

from memu.storage.sqlite_db import SQLiteDB
from memu.storage.vector_db import SimpleVectorDB


class DatabaseMigrator:
    """Utility for database schema migrations and upgrades."""

    def __init__(self, db_path: str, vector_db_path: str):
        self.db_path = pathlib.Path(db_path)
        self.vector_db_path = pathlib.Path(vector_db_path)

    def migrate_to_latest(self) -> None:
        """Apply all pending migrations to reach the latest schema version."""
        # Initialize databases (creates schema if not exists)
        db = SQLiteDB(str(self.db_path))
        vector_db = SimpleVectorDB(str(self.vector_db_path))

        # Close connections
        db.close()
        vector_db.close()

        print(f"Database initialized at: {self.db_path}")
        print(f"Vector database initialized at: {self.vector_db_path}")

    def reset_database(self) -> None:
        """Reset the database by removing all data files."""
        if self.db_path.exists():
            self.db_path.unlink()
            print(f"Removed database: {self.db_path}")

        if self.vector_db_path.exists():
            self.vector_db_path.unlink()
            print(f"Removed vector database: {self.vector_db_path}")

        print("Database reset complete.")

    def backup_database(self, backup_path: str) -> None:
        """Create a backup of the current database."""
        import shutil

        backup_dir = pathlib.Path(backup_path)
        backup_dir.mkdir(parents=True, exist_ok=True)

        if self.db_path.exists():
            db_backup = backup_dir / f"{self.db_path.name}.backup"
            shutil.copy2(self.db_path, db_backup)
            print(f"Database backed up to: {db_backup}")

        if self.vector_db_path.exists():
            vector_backup = backup_dir / f"{self.vector_db_path.name}.backup"
            shutil.copy2(self.vector_db_path, vector_backup)
            print(f"Vector database backed up to: {vector_backup}")


def migrate_database(db_path: str = "./data/memu.db", vector_db_path: str = "./data/vectors.json") -> None:
    """Convenience function to migrate database to latest version."""
    migrator = DatabaseMigrator(db_path, vector_db_path)
    migrator.migrate_to_latest()


def reset_database(db_path: str = "./data/memu.db", vector_db_path: str = "./data/vectors.json") -> None:
    """Convenience function to reset database."""
    migrator = DatabaseMigrator(db_path, vector_db_path)
    migrator.reset_database()


def backup_database(
    db_path: str = "./data/memu.db",
    vector_db_path: str = "./data/vectors.json",
    backup_path: str = "./data/backups",
) -> None:
    """Convenience function to backup database."""
    migrator = DatabaseMigrator(db_path, vector_db_path)
    migrator.backup_database(backup_path)
