"""Extract and save raw 2026 FIFA World Cup data.

This script retrieves World Cup competition and match data from
football-data.org, then saves timestamped JSON files locally.

Generated files are saved under:

    data/raw/api/

The raw files are ignored by Git.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException


# Make the project root importable when running as a module.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    FOOTBALL_DATA_API_KEY,
    FOOTBALL_DATA_BASE_URL,
    RAW_API_DIR,
    WORLD_CUP_COMPETITION_CODE,
    validate_api_configuration,
)


REQUEST_TIMEOUT_SECONDS = 30
TARGET_TEAMS = ("Spain", "Argentina")


def create_headers() -> dict[str, str]:
    """Create HTTP headers required by football-data.org."""

    return {
        "X-Auth-Token": FOOTBALL_DATA_API_KEY, # type: ignore
        "Accept": "application/json",
    }


def request_json(endpoint: str) -> dict[str, Any]:
    """Request one API endpoint and return the decoded JSON response."""

    url = f"{FOOTBALL_DATA_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    try:
        response: Response = requests.get(
            url,
            headers=create_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    except requests.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else "unknown"
        )

        if status_code == 401:
            explanation = "The API token is missing or invalid."
        elif status_code == 403:
            explanation = "The account cannot access this resource."
        elif status_code == 404:
            explanation = "The requested API endpoint was not found."
        elif status_code == 429:
            explanation = "The API request limit was exceeded."
        else:
            explanation = "The API returned an unsuccessful response."

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
            f"The API response from {url} was not valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise TypeError(
            "Expected the API response to be a JSON object, "
            f"but received {type(payload).__name__}."
        )

    return payload


def save_json(
    payload: dict[str, Any],
    filename: str,
) -> Path:
    """Save a dictionary as a formatted UTF-8 JSON file."""

    RAW_API_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_API_DIR / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def get_team_name(match: dict[str, Any], side: str) -> str:
    """Return a team name from a match's homeTeam or awayTeam field."""

    team_data = match.get(side) or {}

    if not isinstance(team_data, dict):
        return ""

    return str(team_data.get("name") or "").strip()


def match_contains_team(
    match: dict[str, Any],
    team_name: str,
) -> bool:
    """Return True when the specified team appears in a match."""

    normalized_target = team_name.casefold()

    home_team = get_team_name(match, "homeTeam").casefold()
    away_team = get_team_name(match, "awayTeam").casefold()

    return (
        normalized_target == home_team
        or normalized_target == away_team
    )


def filter_team_matches(
    matches: list[dict[str, Any]],
    team_name: str,
) -> list[dict[str, Any]]:
    """Return every match involving the specified team."""

    return [
        match
        for match in matches
        if match_contains_team(match, team_name)
    ]


def create_team_payload(
    team_name: str,
    matches: list[dict[str, Any]],
    extracted_at: str,
) -> dict[str, Any]:
    """Create a documented raw payload for one selected team."""

    return {
        "metadata": {
            "team_name": team_name,
            "competition_code": WORLD_CUP_COMPETITION_CODE,
            "extracted_at_utc": extracted_at,
            "source": "football-data.org API v4",
            "match_count": len(matches),
        },
        "matches": matches,
    }


def create_manifest(
    extracted_at: str,
    files: dict[str, Path],
    total_matches: int,
    team_match_counts: dict[str, int],
) -> dict[str, Any]:
    """Create metadata describing one extraction run."""

    return {
        "extraction": {
            "extracted_at_utc": extracted_at,
            "api_base_url": FOOTBALL_DATA_BASE_URL,
            "competition_code": WORLD_CUP_COMPETITION_CODE,
            "source": "football-data.org API v4",
            "total_world_cup_matches": total_matches,
            "target_teams": list(TARGET_TEAMS),
        },
        "team_match_counts": team_match_counts,
        "generated_files": {
            name: str(path.relative_to(PROJECT_ROOT))
            for name, path in files.items()
        },
    }


def print_match_summary(
    team_name: str,
    matches: list[dict[str, Any]],
) -> None:
    """Print a readable summary of a selected team's matches."""

    print(f"\n{team_name} matches returned: {len(matches)}")

    for match in matches:
        home_team = get_team_name(match, "homeTeam")
        away_team = get_team_name(match, "awayTeam")

        score = match.get("score") or {}
        full_time = score.get("fullTime") or {}

        home_score = full_time.get("home")
        away_score = full_time.get("away")

        print(
            f"  {match.get('utcDate')} | "
            f"{match.get('stage')} | "
            f"{home_team} {home_score}-{away_score} {away_team} | "
            f"{match.get('status')}"
        )


def main() -> None:
    """Run the complete raw World Cup extraction process."""

    validate_api_configuration()

    extracted_at_datetime = datetime.now(timezone.utc)
    extracted_at = extracted_at_datetime.isoformat()
    timestamp = extracted_at_datetime.strftime("%Y%m%d_%H%M%S")

    print("Starting World Cup data extraction...")
    print(f"Extraction timestamp: {extracted_at}")
    print(f"Competition code: {WORLD_CUP_COMPETITION_CODE}")

    competition_payload = request_json(
        f"/competitions/{WORLD_CUP_COMPETITION_CODE}"
    )

    matches_payload = request_json(
        f"/competitions/{WORLD_CUP_COMPETITION_CODE}/matches"
    )

    matches = matches_payload.get("matches", [])

    if not isinstance(matches, list):
        raise TypeError(
            "Expected the 'matches' field to contain a list."
        )

    if not matches:
        raise ValueError(
            "The API returned zero World Cup matches."
        )

    invalid_match_records = [
        match
        for match in matches
        if not isinstance(match, dict)
    ]

    if invalid_match_records:
        raise TypeError(
            "One or more match records were not JSON objects."
        )

    files: dict[str, Path] = {}

    competition_filename = (
        f"world_cup_competition_{timestamp}.json"
    )
    matches_filename = (
        f"world_cup_matches_{timestamp}.json"
    )

    files["competition"] = save_json(
        competition_payload,
        competition_filename,
    )

    files["all_matches"] = save_json(
        matches_payload,
        matches_filename,
    )

    team_match_counts: dict[str, int] = {}

    for team_name in TARGET_TEAMS:
        team_matches = filter_team_matches(matches, team_name)
        team_match_counts[team_name] = len(team_matches)

        team_payload = create_team_payload(
            team_name=team_name,
            matches=team_matches,
            extracted_at=extracted_at,
        )

        safe_team_name = team_name.lower().replace(" ", "_")
        filename = f"{safe_team_name}_matches_{timestamp}.json"

        files[f"{safe_team_name}_matches"] = save_json(
            team_payload,
            filename,
        )

        print_match_summary(team_name, team_matches)

    manifest = create_manifest(
        extracted_at=extracted_at,
        files=files,
        total_matches=len(matches),
        team_match_counts=team_match_counts,
    )

    manifest_filename = (
        f"extraction_manifest_{timestamp}.json"
    )

    manifest_path = save_json(
        manifest,
        manifest_filename,
    )

    files["manifest"] = manifest_path

    print("\nExtraction completed successfully.")
    print(f"Total World Cup matches saved: {len(matches)}")

    print("\nGenerated files:")

    for name, path in files.items():
        relative_path = path.relative_to(PROJECT_ROOT)
        print(f"  {name}: {relative_path}")


if __name__ == "__main__":
    main()