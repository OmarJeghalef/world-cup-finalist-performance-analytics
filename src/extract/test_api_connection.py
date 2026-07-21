"""Test connectivity to football-data.org and inspect available competitions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException

# Allow the script to import modules from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    FOOTBALL_DATA_API_KEY,
    FOOTBALL_DATA_BASE_URL,
    WORLD_CUP_COMPETITION_CODE,
    validate_api_configuration,
)


REQUEST_TIMEOUT_SECONDS = 30


def create_headers() -> dict[str, str]:
    """Create the authentication headers required by football-data.org."""

    return {
        "X-Auth-Token": FOOTBALL_DATA_API_KEY, # type: ignore
        "Accept": "application/json",
    }


def request_json(endpoint: str) -> dict[str, Any]:
    """Request one API endpoint and return its decoded JSON object."""

    url = f"{FOOTBALL_DATA_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    try:
        response: Response = requests.get(
            url,
            headers=create_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response else "unknown"

        if status_code == 401:
            explanation = "The API token is missing or invalid."
        elif status_code == 403:
            explanation = "Your subscription cannot access this resource."
        elif status_code == 404:
            explanation = "The requested API resource was not found."
        elif status_code == 429:
            explanation = "The API request limit was exceeded."
        else:
            explanation = "The API returned an unsuccessful HTTP status."

        raise RuntimeError(
            f"{explanation} Status: {status_code}. URL: {url}"
        ) from exc

    except RequestException as exc:
        raise RuntimeError(
            f"Could not connect to football-data.org. URL: {url}"
        ) from exc

    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        raise RuntimeError(
            "The API response was not valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise TypeError(
            f"Expected a JSON object but received {type(payload).__name__}."
        )

    return payload


def find_world_cup(
    competitions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the World Cup competition by code or name."""

    for competition in competitions:
        code = str(competition.get("code", "")).upper()
        name = str(competition.get("name", "")).lower()

        if code == WORLD_CUP_COMPETITION_CODE.upper():
            return competition

        if "world cup" in name or "worldcup" in name:
            return competition

    return None


def main() -> None:
    """Validate configuration and perform introductory API requests."""

    validate_api_configuration()

    print("Testing football-data.org API connection...")
    print(f"Base URL: {FOOTBALL_DATA_BASE_URL}")

    competitions_payload = request_json("/competitions")
    competitions = competitions_payload.get("competitions", [])

    if not isinstance(competitions, list):
        raise TypeError(
            "Expected the 'competitions' field to contain a list."
        )

    print(f"Connection successful.")
    print(f"Accessible competitions returned: {len(competitions)}")

    world_cup = find_world_cup(competitions)

    if world_cup is None:
        print(
            "\nThe World Cup was not found in the authenticated "
            "competition list."
        )
        print(
            "We will inspect the unrestricted competition catalogue "
            "and your account coverage next."
        )
        return

    print("\nWorld Cup competition found:")
    print(f"  ID: {world_cup.get('id')}")
    print(f"  Name: {world_cup.get('name')}")
    print(f"  Code: {world_cup.get('code')}")
    print(f"  Type: {world_cup.get('type')}")

    current_season = world_cup.get("currentSeason") or {}

    if current_season:
        print("\nCurrent season:")
        print(f"  Season ID: {current_season.get('id')}")
        print(f"  Start date: {current_season.get('startDate')}")
        print(f"  End date: {current_season.get('endDate')}")
        print(f"  Current matchday: {current_season.get('currentMatchday')}")

    competition_code = world_cup.get("code") or WORLD_CUP_COMPETITION_CODE

    matches_payload = request_json(
        f"/competitions/{competition_code}/matches"
    )
    matches = matches_payload.get("matches", [])

    if not isinstance(matches, list):
        raise TypeError("Expected the 'matches' field to contain a list.")

    print(f"\nWorld Cup matches returned: {len(matches)}")

    if matches:
        first_match = matches[0]
        home_team = (first_match.get("homeTeam") or {}).get("name")
        away_team = (first_match.get("awayTeam") or {}).get("name")

        print("\nSample match:")
        print(f"  Match ID: {first_match.get('id')}")
        print(f"  Date: {first_match.get('utcDate')}")
        print(f"  Stage: {first_match.get('stage')}")
        print(f"  Status: {first_match.get('status')}")
        print(f"  Teams: {home_team} vs. {away_team}")

    print("\nAPI connection test completed successfully.")


if __name__ == "__main__":
    main()