"""Transform raw World Cup API data into analysis-ready CSV files.

The script reads the newest raw World Cup match JSON file, flattens the
nested API response, and creates three processed datasets:

    data/processed/teams.csv
    data/processed/matches.csv
    data/processed/team_match_performance.csv

The team-match dataset contains one row per team per match.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    PROCESSED_DATA_DIR,
    RAW_API_DIR,
)


TARGET_TEAMS = {"Spain", "Argentina"}


def find_latest_file(
    directory: Path,
    pattern: str,
) -> Path:
    """Return the most recently named file matching a glob pattern."""

    matching_files = sorted(directory.glob(pattern))

    if not matching_files:
        raise FileNotFoundError(
            f"No files matching '{pattern}' were found in {directory}."
        )

    return matching_files[-1]


def load_json(path: Path) -> dict[str, Any]:
    """Load and validate one JSON object from disk."""

    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"The file is not valid JSON: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise TypeError(
            f"Expected a JSON object in {path}, "
            f"but received {type(payload).__name__}."
        )

    return payload


def get_nested_dictionary(
    record: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    """Return a nested dictionary or an empty dictionary."""

    value = record.get(key)

    if isinstance(value, dict):
        return value

    return {}


def get_score_value(
    score_section: dict[str, Any],
    side: str,
) -> int | None:
    """Return a score value while supporting common API key variants.

    football-data.org documentation commonly shows keys such as homeTeam and
    awayTeam, while some list responses or versions may use home and away.
    """

    key_options = {
        "home": ("home", "homeTeam"),
        "away": ("away", "awayTeam"),
    }

    for key in key_options[side]:
        value = score_section.get(key)

        if value is not None:
            return int(value)

    return None


def normalize_stage(stage: Any) -> str:
    """Convert an API stage value into a stable string."""

    if stage is None:
        return "UNKNOWN"

    return str(stage).strip().upper()


def determine_result(
    goals_scored: int | None,
    goals_conceded: int | None,
    winner: str | None,
    team_side: str,
    status: str,
) -> str | None:
    """Determine a team's result from its perspective."""

    if status != "FINISHED":
        return None

    if winner == "DRAW":
        return "D"

    expected_winner = (
        "HOME_TEAM"
        if team_side == "HOME"
        else "AWAY_TEAM"
    )

    if winner == expected_winner:
        return "W"

    if winner in {"HOME_TEAM", "AWAY_TEAM"}:
        return "L"

    if goals_scored is None or goals_conceded is None:
        return None

    if goals_scored > goals_conceded:
        return "W"

    if goals_scored < goals_conceded:
        return "L"

    return "D"


def transform_teams(
    matches: list[dict[str, Any]],
) -> pd.DataFrame:
    """Create one unique row per team."""

    team_records: dict[int, dict[str, Any]] = {}

    for match in matches:
        for side_key in ("homeTeam", "awayTeam"):
            team = get_nested_dictionary(match, side_key)
            team_id = team.get("id")

            if team_id is None:
                continue

            team_records[int(team_id)] = {
                "team_id": int(team_id),
                "team_name": team.get("name"),
                "short_name": team.get("shortName"),
                "team_code": team.get("tla"),
                "crest_url": team.get("crest"),
                "is_selected_finalist": (
                    str(team.get("name")) in TARGET_TEAMS
                ),
            }

    teams_df = pd.DataFrame(team_records.values())

    if teams_df.empty:
        raise ValueError("No team records could be created.")

    teams_df = teams_df.sort_values(
        by=["team_name", "team_id"],
        na_position="last",
    ).reset_index(drop=True)

    return teams_df


def transform_matches(
    matches: list[dict[str, Any]],
) -> pd.DataFrame:
    """Create one flattened row per match."""

    records: list[dict[str, Any]] = []

    for match in matches:
        competition = get_nested_dictionary(match, "competition")
        season = get_nested_dictionary(match, "season")
        home_team = get_nested_dictionary(match, "homeTeam")
        away_team = get_nested_dictionary(match, "awayTeam")
        score = get_nested_dictionary(match, "score")

        full_time = get_nested_dictionary(score, "fullTime")
        half_time = get_nested_dictionary(score, "halfTime")
        regular_time = get_nested_dictionary(score, "regularTime")
        extra_time = get_nested_dictionary(score, "extraTime")
        penalties = get_nested_dictionary(score, "penalties")

        records.append(
            {
                "match_id": match.get("id"),
                "competition_id": competition.get("id"),
                "competition_name": competition.get("name"),
                "competition_code": competition.get("code"),
                "season_id": season.get("id"),
                "season_start_date": season.get("startDate"),
                "season_end_date": season.get("endDate"),
                "match_date_utc": match.get("utcDate"),
                "status": match.get("status"),
                "stage": normalize_stage(match.get("stage")),
                "group_name": match.get("group"),
                "matchday": match.get("matchday"),
                "venue": match.get("venue"),
                "attendance": match.get("attendance"),
                "home_team_id": home_team.get("id"),
                "home_team_name": home_team.get("name"),
                "away_team_id": away_team.get("id"),
                "away_team_name": away_team.get("name"),
                "winner": score.get("winner"),
                "duration": score.get("duration"),
                "full_time_home_goals": get_score_value(
                    full_time,
                    "home",
                ),
                "full_time_away_goals": get_score_value(
                    full_time,
                    "away",
                ),
                "half_time_home_goals": get_score_value(
                    half_time,
                    "home",
                ),
                "half_time_away_goals": get_score_value(
                    half_time,
                    "away",
                ),
                "regular_time_home_goals": get_score_value(
                    regular_time,
                    "home",
                ),
                "regular_time_away_goals": get_score_value(
                    regular_time,
                    "away",
                ),
                "extra_time_home_goals": get_score_value(
                    extra_time,
                    "home",
                ),
                "extra_time_away_goals": get_score_value(
                    extra_time,
                    "away",
                ),
                "penalty_home_goals": get_score_value(
                    penalties,
                    "home",
                ),
                "penalty_away_goals": get_score_value(
                    penalties,
                    "away",
                ),
                "last_updated_utc": match.get("lastUpdated"),
            }
        )

    matches_df = pd.DataFrame(records)

    if matches_df.empty:
        raise ValueError("No match records could be created.")

    datetime_columns = [
        "match_date_utc",
        "last_updated_utc",
    ]

    for column in datetime_columns:
        matches_df[column] = pd.to_datetime(
            matches_df[column],
            errors="coerce",
            utc=True,
        )

    date_columns = [
        "season_start_date",
        "season_end_date",
    ]

    for column in date_columns:
        matches_df[column] = pd.to_datetime(
            matches_df[column],
            errors="coerce",
        ).dt.date

    integer_columns = [
        "match_id",
        "competition_id",
        "season_id",
        "matchday",
        "attendance",
        "home_team_id",
        "away_team_id",
        "full_time_home_goals",
        "full_time_away_goals",
        "half_time_home_goals",
        "half_time_away_goals",
        "regular_time_home_goals",
        "regular_time_away_goals",
        "extra_time_home_goals",
        "extra_time_away_goals",
        "penalty_home_goals",
        "penalty_away_goals",
    ]

    for column in integer_columns:
        matches_df[column] = pd.to_numeric(
            matches_df[column],
            errors="coerce",
        ).astype("Int64")

    matches_df["went_to_extra_time"] = matches_df[
        "duration"
    ].isin(["EXTRA_TIME", "PENALTY_SHOOTOUT"])

    matches_df["went_to_penalties"] = (
        matches_df["duration"] == "PENALTY_SHOOTOUT"
    )

    matches_df["involves_selected_finalist"] = (
        matches_df["home_team_name"].isin(TARGET_TEAMS)
        | matches_df["away_team_name"].isin(TARGET_TEAMS)
    )

    matches_df = matches_df.sort_values(
        by=["match_date_utc", "match_id"],
        na_position="last",
    ).reset_index(drop=True)

    return matches_df


def build_team_performance_row(
    match: pd.Series,
    team_side: str,
) -> dict[str, Any]:
    """Create one team-perspective row from a match record."""

    is_home = team_side == "HOME"

    if is_home:
        team_id = match["home_team_id"]
        team_name = match["home_team_name"]
        opponent_id = match["away_team_id"]
        opponent_name = match["away_team_name"]
        goals_scored = match["full_time_home_goals"]
        goals_conceded = match["full_time_away_goals"]
        penalty_goals_scored = match["penalty_home_goals"]
        penalty_goals_conceded = match["penalty_away_goals"]
    else:
        team_id = match["away_team_id"]
        team_name = match["away_team_name"]
        opponent_id = match["home_team_id"]
        opponent_name = match["home_team_name"]
        goals_scored = match["full_time_away_goals"]
        goals_conceded = match["full_time_home_goals"]
        penalty_goals_scored = match["penalty_away_goals"]
        penalty_goals_conceded = match["penalty_home_goals"]

    result = determine_result(
        goals_scored=(
            None
            if pd.isna(goals_scored)
            else int(goals_scored)
        ),
        goals_conceded=(
            None
            if pd.isna(goals_conceded)
            else int(goals_conceded)
        ),
        winner=match["winner"],
        team_side=team_side,
        status=match["status"],
    )

    if pd.isna(goals_scored) or pd.isna(goals_conceded):
        goal_difference = pd.NA
        clean_sheet = pd.NA
        win_margin = pd.NA
    else:
        goal_difference = int(goals_scored - goals_conceded)
        clean_sheet = int(goals_conceded) == 0
        win_margin = (
            int(goals_scored - goals_conceded)
            if result == "W"
            else 0
        )

    return {
        "team_match_id": f"{match['match_id']}_{team_id}",
        "match_id": match["match_id"],
        "match_date_utc": match["match_date_utc"],
        "stage": match["stage"],
        "group_name": match["group_name"],
        "status": match["status"],
        "team_id": team_id,
        "team_name": team_name,
        "opponent_team_id": opponent_id,
        "opponent_name": opponent_name,
        "venue_side": team_side,
        "goals_scored": goals_scored,
        "goals_conceded": goals_conceded,
        "goal_difference": goal_difference,
        "result": result,
        "win": result == "W",
        "draw": result == "D",
        "loss": result == "L",
        "clean_sheet": clean_sheet,
        "win_margin": win_margin,
        "duration": match["duration"],
        "went_to_extra_time": match["went_to_extra_time"],
        "went_to_penalties": match["went_to_penalties"],
        "penalty_goals_scored": penalty_goals_scored,
        "penalty_goals_conceded": penalty_goals_conceded,
        "is_selected_finalist": team_name in TARGET_TEAMS,
    }


def transform_team_match_performance(
    matches_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create two team-perspective rows for every match."""

    records: list[dict[str, Any]] = []

    for _, match in matches_df.iterrows():
        records.append(
            build_team_performance_row(match, "HOME")
        )
        records.append(
            build_team_performance_row(match, "AWAY")
        )

    performance_df = pd.DataFrame(records)

    if performance_df.empty:
        raise ValueError(
            "No team-match performance records could be created."
        )

    integer_columns = [
        "match_id",
        "team_id",
        "opponent_team_id",
        "goals_scored",
        "goals_conceded",
        "goal_difference",
        "win_margin",
        "penalty_goals_scored",
        "penalty_goals_conceded",
    ]

    for column in integer_columns:
        performance_df[column] = pd.to_numeric(
            performance_df[column],
            errors="coerce",
        ).astype("Int64")

    performance_df = performance_df.sort_values(
        by=[
            "match_date_utc",
            "match_id",
            "venue_side",
        ],
        na_position="last",
    ).reset_index(drop=True)

    performance_df["team_match_number"] = (
        performance_df.groupby("team_id")
        .cumcount()
        .add(1)
        .astype("Int64")
    )

    performance_df["cumulative_goals_scored"] = (
        performance_df.groupby("team_id")["goals_scored"]
        .cumsum()
        .astype("Int64")
    )

    performance_df["cumulative_goals_conceded"] = (
        performance_df.groupby("team_id")["goals_conceded"]
        .cumsum()
        .astype("Int64")
    )

    performance_df["cumulative_goal_difference"] = (
        performance_df.groupby("team_id")["goal_difference"]
        .cumsum()
        .astype("Int64")
    )

    return performance_df


def save_dataframe(
    dataframe: pd.DataFrame,
    filename: str,
) -> Path:
    """Save a DataFrame as a UTF-8 CSV file."""

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = PROCESSED_DATA_DIR / filename

    dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8",
    )

    return output_path


def print_selected_team_summary(
    performance_df: pd.DataFrame,
) -> None:
    """Print a small summary for Spain and Argentina."""

    selected = performance_df[
        performance_df["is_selected_finalist"]
    ].copy()

    if selected.empty:
        print("\nNo selected finalist records were found.")
        return

    summary = (
        selected.groupby("team_name", as_index=False)
        .agg(
            matches=("match_id", "count"),
            wins=("win", "sum"),
            draws=("draw", "sum"),
            losses=("loss", "sum"),
            goals_scored=("goals_scored", "sum"),
            goals_conceded=("goals_conceded", "sum"),
            goal_difference=("goal_difference", "sum"),
            clean_sheets=("clean_sheet", "sum"),
        )
    )

    print("\nSelected finalist summary:")
    print(summary.to_string(index=False))


def main() -> None:
    """Run the complete transformation process."""

    raw_matches_path = find_latest_file(
        RAW_API_DIR,
        "world_cup_matches_*.json",
    )

    print("Starting World Cup data transformation...")
    print(f"Raw source: {raw_matches_path.relative_to(PROJECT_ROOT)}")

    payload = load_json(raw_matches_path)
    matches = payload.get("matches")

    if not isinstance(matches, list):
        raise TypeError(
            "The raw file does not contain a valid 'matches' list."
        )

    if not matches:
        raise ValueError(
            "The raw file contains zero match records."
        )

    invalid_records = [
        record
        for record in matches
        if not isinstance(record, dict)
    ]

    if invalid_records:
        raise TypeError(
            "One or more raw match records are not JSON objects."
        )

    teams_df = transform_teams(matches)
    matches_df = transform_matches(matches)
    performance_df = transform_team_match_performance(
        matches_df
    )

    teams_path = save_dataframe(
        teams_df,
        "teams.csv",
    )

    matches_path = save_dataframe(
        matches_df,
        "matches.csv",
    )

    performance_path = save_dataframe(
        performance_df,
        "team_match_performance.csv",
    )

    print("\nTransformation completed successfully.")
    print(f"Teams created: {len(teams_df)}")
    print(f"Matches created: {len(matches_df)}")
    print(
        "Team-match performance rows created: "
        f"{len(performance_df)}"
    )

    print("\nGenerated files:")
    print(f"  {teams_path.relative_to(PROJECT_ROOT)}")
    print(f"  {matches_path.relative_to(PROJECT_ROOT)}")
    print(f"  {performance_path.relative_to(PROJECT_ROOT)}")

    print_selected_team_summary(performance_df)


if __name__ == "__main__":
    main()