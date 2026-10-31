import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_path: Path
    prepared_dir: Path
    pages_per_rater: int = 50

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.environ.get("MRI_DB_PATH", REPO_ROOT / "data" / "app.db")),
            prepared_dir=Path(
                os.environ.get("MRI_PREPARED_DIR", REPO_ROOT / "data" / "prepared")
            ),
            pages_per_rater=int(os.environ.get("MRI_PAGES_PER_RATER", "50")),
        )
