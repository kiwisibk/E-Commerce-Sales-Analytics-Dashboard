"""
Data ingestion module for the Brazilian E-Commerce public dataset by Olist.

Downloads dataset files via the Kaggle API and extracts them into the local 'data/' directory.
Uses pathlib for robust cross-platform path resolution and directory management.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path so modules inside src can be imported cleanly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging for clear status reporting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
KAGGLE_DATASET_SLUG = "olistbr/brazilian-ecommerce"
REQUIRED_DATASET_FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_customers_dataset.csv",
]


def get_default_data_dir() -> Path:
    """
    Dynamically resolve the project's 'data' directory relative to this script.

    Returns:
        Path: Absolute pathlib.Path object pointing to the data directory.
    """
    # Resolve repository root as two levels up from this script (src/ -> root)
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    return data_dir


def check_existing_files(data_dir: Path) -> bool:
    """
    Verify whether all required dataset CSV files already exist in the target directory.

    Args:
        data_dir (Path): The directory to inspect.

    Returns:
        bool: True if all required files exist, False otherwise.
    """
    if not data_dir.exists():
        return False

    existing_files = [f.name for f in data_dir.iterdir() if f.is_file()]
    missing_files = [f for f in REQUIRED_DATASET_FILES if f not in existing_files]

    if not missing_files:
        logger.info("All required dataset files are already present in: %s", data_dir)
        return True

    logger.info("Missing files in %s: %s", data_dir, missing_files)
    return False


def verify_kaggle_credentials() -> bool:
    """
    Verify whether Kaggle API credentials are configured via environment variables,
    OAuth tokens, or legacy ~/.kaggle/kaggle.json credentials file.

    Returns:
        bool: True if credentials are detected, False otherwise.
    """
    # Check modern Kaggle 2.x API token environment variable
    if os.getenv("KAGGLE_API_TOKEN"):
        return True

    # Check legacy environment variables (KAGGLE_USERNAME + KAGGLE_KEY)
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return True

    # Check OAuth cached token or access token in ~/.kaggle/
    kaggle_dir = Path.home() / ".kaggle"
    if (kaggle_dir / "access_token").is_file():
        return True

    # Check legacy ~/.kaggle/kaggle.json file
    if (kaggle_dir / "kaggle.json").is_file():
        return True

    return False


def fetch_kaggle_dataset(
    data_dir: Path | None = None,
    force_download: bool = False,
) -> bool:
    """
    Download and extract the Olist Brazilian E-Commerce dataset using Kaggle's Python API.

    Args:
        data_dir (Path, optional): Destination folder for the dataset. Defaults to project 'data/'.
        force_download (bool): If True, re-downloads even if files already exist.

    Returns:
        bool: True if download succeeded or files already exist, False if failed.
    """
    if data_dir is None:
        data_dir = get_default_data_dir()

    # Ensure target directory exists safely
    data_dir.mkdir(parents=True, exist_ok=True)

    # Check if files already exist
    if not force_download and check_existing_files(data_dir):
        logger.info("Skipping download because required dataset files are already available.")
        return True

    # Validate credentials before attempting API call
    if not verify_kaggle_credentials():
        logger.error(
            "Kaggle API credentials not found.\n"
            "Please ensure you have configured your credentials:\n"
            "  1. Go to https://www.kaggle.com/settings -> 'Create New Token'\n"
            "  2. Place 'kaggle.json' in '%s'\n"
            "  OR set KAGGLE_USERNAME and KAGGLE_KEY environment variables.",
            Path.home() / ".kaggle" / "kaggle.json",
        )
        return False

    try:
        # Import Kaggle API lazily to provide clear error message if kaggle package is not installed
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        logger.info("Authenticating with Kaggle API...")
        api.authenticate()

        logger.info("Downloading dataset '%s' to '%s' (with unzip)...", KAGGLE_DATASET_SLUG, data_dir)
        api.dataset_download_files(
            dataset=KAGGLE_DATASET_SLUG,
            path=str(data_dir),
            unzip=True,
            quiet=False,
        )
        logger.info("Dataset successfully downloaded and extracted into: %s", data_dir)
        return True

    except Exception as exc:
        logger.error("Failed to download dataset from Kaggle: %s", exc)
        return False


def generate_sample_dataset_if_requested(data_dir: Path) -> None:
    """
    Generate realistic sample data directly into the target data directory.
    Useful for offline testing or when Kaggle API credentials are not yet configured.

    Args:
        data_dir (Path): Destination folder for the sample CSV files.
    """
    # Import the generator from the data processing module
    from src.data_processing import generate_sample_dataset

    logger.info("Generating realistic sample dataset in: %s", data_dir)
    generate_sample_dataset(data_dir=data_dir)
    logger.info("Sample dataset generated successfully.")


def main() -> None:
    """
    Entry point for CLI execution of the data fetch routine.
    """
    parser = argparse.ArgumentParser(
        description="Download and extract Brazilian E-Commerce dataset from Kaggle into data/."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Optional custom output directory path. Defaults to <project_root>/data.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if dataset files already exist locally.",
    )
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Generate synthetic Brazilian E-Commerce sample data for offline testing without Kaggle API credentials.",
    )

    args = parser.parse_args()
    target_data_dir = Path(args.data_dir).resolve() if args.data_dir else get_default_data_dir()

    if args.generate_sample:
        generate_sample_dataset_if_requested(target_data_dir)
        sys.exit(0)

    success = fetch_kaggle_dataset(data_dir=target_data_dir, force_download=args.force)
    if not success:
        logger.warning(
            "Download could not be completed via Kaggle API. "
            "You can run 'python src/fetch_data.py --generate-sample' to create sample data for immediate dashboard preview."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
