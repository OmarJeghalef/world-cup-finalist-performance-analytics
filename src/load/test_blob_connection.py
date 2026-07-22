"""Test the Azure Blob Storage connection."""

from __future__ import annotations

import sys
from pathlib import Path

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobServiceClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    AZURE_PROCESSED_CONTAINER,
    AZURE_RAW_CONTAINER,
    AZURE_STORAGE_ACCOUNT_NAME,
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_VALIDATION_CONTAINER,
    validate_azure_storage_configuration,
)


def main() -> None:
    """Connect to Azure and display project containers."""

    validate_azure_storage_configuration()

    print("Testing Azure Blob Storage connection...")
    print(
        "Storage account: "
        f"{AZURE_STORAGE_ACCOUNT_NAME}"
    )

    try:
        client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING #type: ignore
        )

        account_information = (
            client.get_account_information()
        )

        print("Connection successful.")
        print(
            "Account kind: "
            f"{account_information.get('account_kind')}"
        )
        print(
            "SKU name: "
            f"{account_information.get('sku_name')}"
        )

        expected_containers = {
            AZURE_RAW_CONTAINER,
            AZURE_PROCESSED_CONTAINER,
            AZURE_VALIDATION_CONTAINER,
        }

        available_containers = {
            container["name"]
            for container in client.list_containers()
        }

        print("\nExpected project containers:")

        for container_name in sorted(
            expected_containers
        ):
            status = (
                "FOUND"
                if container_name in available_containers
                else "MISSING"
            )

            print(
                f"  [{status}] {container_name}"
            )

        missing_containers = (
            expected_containers - available_containers
        )

        if missing_containers:
            raise RuntimeError(
                "Missing containers: "
                f"{sorted(missing_containers)}"
            )

    except AzureError as exc:
        raise RuntimeError(
            "Could not connect to Azure Blob Storage."
        ) from exc

    print(
        "\nAzure Blob Storage connection test "
        "completed successfully."
    )


if __name__ == "__main__":
    main()