"""Upload World Cup pipeline outputs to Azure Blob Storage.

The script uploads:

- Raw API JSON files to the raw container
- Processed CSV files to the processed container
- Validation reports to the validation container

Files are organized inside each container using virtual folder prefixes.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from azure.core.exceptions import (
    AzureError,
    ResourceExistsError,
)
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    AZURE_PROCESSED_CONTAINER,
    AZURE_RAW_CONTAINER,
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_VALIDATION_CONTAINER,
    PROCESSED_DATA_DIR,
    RAW_API_DIR,
    VALIDATION_DIR,
    validate_azure_storage_configuration,
)


@dataclass(frozen=True)
class UploadSource:
    """Describe one local directory and Azure destination."""

    local_directory: Path
    container_name: str
    blob_prefix: str
    patterns: tuple[str, ...]


UPLOAD_SOURCES = (
    UploadSource(
        local_directory=RAW_API_DIR,
        container_name=AZURE_RAW_CONTAINER,
        blob_prefix="football-data-api",
        patterns=("*.json",),
    ),
    UploadSource(
        local_directory=PROCESSED_DATA_DIR,
        container_name=AZURE_PROCESSED_CONTAINER,
        blob_prefix="world-cup-2026",
        patterns=("*.csv",),
    ),
    UploadSource(
        local_directory=VALIDATION_DIR,
        container_name=AZURE_VALIDATION_CONTAINER,
        blob_prefix="world-cup-2026",
        patterns=("*.json", "*.csv"),
    ),
)


def create_blob_service_client() -> BlobServiceClient:
    """Create an authenticated Azure Blob service client."""

    validate_azure_storage_configuration()

    return BlobServiceClient.from_connection_string(
        AZURE_STORAGE_CONNECTION_STRING #type: ignore
    )


def ensure_container_exists(
    blob_service_client: BlobServiceClient,
    container_name: str,
) -> ContainerClient:
    """Return a container client and create the container if needed."""

    container_client = (
        blob_service_client.get_container_client(
            container_name
        )
    )

    try:
        container_client.create_container()
        print(f"Created container: {container_name}")
    except ResourceExistsError:
        print(f"Container already exists: {container_name}")

    return container_client


def find_files(source: UploadSource) -> list[Path]:
    """Find uploadable files using the configured patterns."""

    files: set[Path] = set()

    for pattern in source.patterns:
        files.update(
            path
            for path in source.local_directory.glob(pattern)
            if path.is_file()
        )

    return sorted(files)


def create_blob_name(
    source: UploadSource,
    file_path: Path,
) -> str:
    """Create the destination blob name for one local file."""

    return f"{source.blob_prefix}/{file_path.name}"


def upload_file(
    container_client: ContainerClient,
    file_path: Path,
    blob_name: str,
) -> None:
    """Upload one file and replace an existing blob with the same name."""

    blob_client = container_client.get_blob_client(
        blob_name
    )

    with file_path.open("rb") as file:
        blob_client.upload_blob(
            file,
            overwrite=True,
        )

    file_size_bytes = file_path.stat().st_size

    print(
        f"Uploaded {file_path.name} "
        f"→ {container_client.container_name}/{blob_name} "
        f"({file_size_bytes:,} bytes)"
    )


def upload_source(
    blob_service_client: BlobServiceClient,
    source: UploadSource,
) -> int:
    """Upload every matching file for one configured source."""

    if not source.local_directory.exists():
        raise FileNotFoundError(
            "Local upload directory does not exist: "
            f"{source.local_directory}"
        )

    files = find_files(source)

    if not files:
        print(
            "No uploadable files found in "
            f"{source.local_directory.relative_to(PROJECT_ROOT)}"
        )
        return 0

    container_client = ensure_container_exists(
        blob_service_client,
        source.container_name,
    )

    uploaded_count = 0

    for file_path in files:
        blob_name = create_blob_name(
            source,
            file_path,
        )

        upload_file(
            container_client=container_client,
            file_path=file_path,
            blob_name=blob_name,
        )

        uploaded_count += 1

    return uploaded_count


def list_uploaded_blobs(
    blob_service_client: BlobServiceClient,
) -> None:
    """List blobs currently stored in each project container."""

    print("\nAzure Blob Storage contents:")

    container_names = (
        AZURE_RAW_CONTAINER,
        AZURE_PROCESSED_CONTAINER,
        AZURE_VALIDATION_CONTAINER,
    )

    for container_name in container_names:
        container_client = (
            blob_service_client.get_container_client(
                container_name
            )
        )

        print(f"\n{container_name}/")

        blob_count = 0

        for blob in container_client.list_blobs():
            blob_count += 1
            size = blob.size or 0

            print(
                f"  {blob.name} "
                f"({size:,} bytes)"
            )

        if blob_count == 0:
            print("  No blobs found.")


def main() -> None:
    """Upload all current pipeline output files."""

    print("Starting Azure Blob Storage upload...")

    try:
        blob_service_client = (
            create_blob_service_client()
        )

        total_uploaded = 0

        for source in UPLOAD_SOURCES:
            relative_directory = (
                source.local_directory.relative_to(
                    PROJECT_ROOT
                )
            )

            print(
                f"\nUploading files from "
                f"{relative_directory} "
                f"to container '{source.container_name}'..."
            )

            total_uploaded += upload_source(
                blob_service_client,
                source,
            )

        list_uploaded_blobs(blob_service_client)

    except AzureError as exc:
        raise RuntimeError(
            "Azure Blob Storage operation failed. "
            "Verify the connection string, storage-account "
            "permissions, container names, and network access."
        ) from exc

    print(
        "\nAzure upload completed successfully."
    )
    print(f"Files uploaded: {total_uploaded}")


if __name__ == "__main__":
    main()