"""Validate processed World Cup datasets before database loading.

This script validates:

    data/processed/teams.csv
    data/processed/matches.csv
    data/processed/team_match_performance.csv

A machine-readable JSON report is saved under:

    data/validation/validation_report.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    PROCESSED_DATA_DIR,
    VALIDATION_DIR,
)


EXPECTED_MATCH_COUNT = 104
EXPECTED_TEAM_MATCH_COUNT = EXPECTED_MATCH_COUNT * 2
SELECTED_TEAMS = {"Spain", "Argentina"}

VALID_STAGES = {
    "GROUP_STAGE",
    "ROUND_OF_32",
    "LAST_32",
    "ROUND_OF_16",
    "LAST_16",
    "QUARTER_FINALS",
    "SEMI_FINALS",
    "THIRD_PLACE",
    "FINAL",
}

VALID_RESULTS = {"W", "D", "L"}
VALID_VENUE_SIDES = {"HOME", "AWAY"}
VALID_DURATIONS = {
    "REGULAR",
    "EXTRA_TIME",
    "PENALTY_SHOOTOUT",
}


class ValidationReport:
    """Collect validation results and create a JSON report."""

    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(
        self,
        name: str,
        passed: bool,
        details: str,
    ) -> None:
        """Add one validation check."""

        self.checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "details": details,
            }
        )

    @property
    def passed(self) -> bool:
        """Return True when every check passed."""

        return all(
            check["passed"]
            for check in self.checks
        )

    def to_dictionary(self) -> dict[str, Any]:
        """Convert the report to a serializable dictionary."""

        return {
            "validated_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "overall_status": (
                "PASSED"
                if self.passed
                else "FAILED"
            ),
            "total_checks": len(self.checks),
            "passed_checks": sum(
                check["passed"]
                for check in self.checks
            ),
            "failed_checks": sum(
                not check["passed"]
                for check in self.checks
            ),
            "checks": self.checks,
        }


def load_csv(
    filename: str,
) -> pd.DataFrame:
    """Load a required processed CSV file."""

    path = PROCESSED_DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Required processed file does not exist: {path}"
        )

    dataframe = pd.read_csv(path)

    if dataframe.empty:
        raise ValueError(
            f"Processed file contains no rows: {path}"
        )

    return dataframe


def check_required_columns(
    report: ValidationReport,
    dataframe: pd.DataFrame,
    dataset_name: str,
    required_columns: set[str],
) -> None:
    """Validate that all required columns exist."""

    missing_columns = sorted(
        required_columns - set(dataframe.columns)
    )

    report.add(
        name=f"{dataset_name}: required columns",
        passed=not missing_columns,
        details=(
            "All required columns are present."
            if not missing_columns
            else f"Missing columns: {missing_columns}"
        ),
    )


def check_non_null(
    report: ValidationReport,
    dataframe: pd.DataFrame,
    dataset_name: str,
    columns: list[str],
) -> None:
    """Validate non-null values for critical fields."""

    null_counts = dataframe[columns].isna().sum()
    invalid = {
        column: int(count)
        for column, count in null_counts.items()
        if count > 0
    }

    report.add(
        name=f"{dataset_name}: critical non-null fields",
        passed=not invalid,
        details=(
            "No null values found in critical fields."
            if not invalid
            else f"Null counts: {invalid}"
        ),
    )


def validate_teams(
    teams_df: pd.DataFrame,
    report: ValidationReport,
) -> None:
    """Validate the teams dataset."""

    required_columns = {
        "team_id",
        "team_name",
        "short_name",
        "team_code",
        "is_selected_finalist",
    }

    check_required_columns(
        report,
        teams_df,
        "teams",
        required_columns,
    )

    if not required_columns.issubset(teams_df.columns):
        return

    check_non_null(
        report,
        teams_df,
        "teams",
        ["team_id", "team_name"],
    )

    duplicate_ids = int(
        teams_df["team_id"].duplicated().sum()
    )

    report.add(
        name="teams: unique team IDs",
        passed=duplicate_ids == 0,
        details=f"Duplicate team IDs: {duplicate_ids}",
    )

    selected_teams_found = set(
        teams_df.loc[
            teams_df["team_name"].isin(SELECTED_TEAMS),
            "team_name",
        ]
    )

    missing_selected = sorted(
        SELECTED_TEAMS - selected_teams_found
    )

    report.add(
        name="teams: selected finalists present",
        passed=not missing_selected,
        details=(
            "Spain and Argentina are present."
            if not missing_selected
            else f"Missing teams: {missing_selected}"
        ),
    )


def validate_matches(
    matches_df: pd.DataFrame,
    report: ValidationReport,
) -> None:
    """Validate the matches dataset."""

    required_columns = {
        "match_id",
        "match_date_utc",
        "status",
        "stage",
        "home_team_id",
        "home_team_name",
        "away_team_id",
        "away_team_name",
        "winner",
        "duration",
        "full_time_home_goals",
        "full_time_away_goals",
    }

    check_required_columns(
        report,
        matches_df,
        "matches",
        required_columns,
    )

    if not required_columns.issubset(matches_df.columns):
        return

    check_non_null(
        report,
        matches_df,
        "matches",
        [
            "match_id",
            "match_date_utc",
            "status",
            "stage",
            "home_team_id",
            "home_team_name",
            "away_team_id",
            "away_team_name",
        ],
    )

    report.add(
        name="matches: expected row count",
        passed=len(matches_df) == EXPECTED_MATCH_COUNT,
        details=(
            f"Expected {EXPECTED_MATCH_COUNT}; "
            f"found {len(matches_df)}."
        ),
    )

    duplicate_match_ids = int(
        matches_df["match_id"].duplicated().sum()
    )

    report.add(
        name="matches: unique match IDs",
        passed=duplicate_match_ids == 0,
        details=f"Duplicate match IDs: {duplicate_match_ids}",
    )

    same_team_mask = (
        matches_df["home_team_id"]
        == matches_df["away_team_id"]
    )

    report.add(
        name="matches: different home and away teams",
        passed=not same_team_mask.any(),
        details=(
            "No match has the same home and away team."
            if not same_team_mask.any()
            else (
                f"Invalid matches: "
                f"{int(same_team_mask.sum())}"
            )
        ),
    )

    parsed_dates = pd.to_datetime(
        matches_df["match_date_utc"],
        errors="coerce",
        utc=True,
    )

    invalid_dates = int(parsed_dates.isna().sum())

    report.add(
        name="matches: valid UTC dates",
        passed=invalid_dates == 0,
        details=f"Invalid dates: {invalid_dates}",
    )

    finished_matches = matches_df[
        matches_df["status"] == "FINISHED"
    ]

    finished_score_nulls = int(
        finished_matches[
            [
                "full_time_home_goals",
                "full_time_away_goals",
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    report.add(
        name="matches: finished matches have scores",
        passed=finished_score_nulls == 0,
        details=(
            "Finished matches missing full-time scores: "
            f"{finished_score_nulls}"
        ),
    )

    score_columns = [
        "full_time_home_goals",
        "full_time_away_goals",
        "penalty_home_goals",
        "penalty_away_goals",
    ]

    negative_scores = 0

    for column in score_columns:
        numeric_values = pd.to_numeric(
            matches_df[column],
            errors="coerce",
        )

        negative_scores += int(
            (numeric_values.dropna() < 0).sum()
        )

    report.add(
        name="matches: non-negative scores",
        passed=negative_scores == 0,
        details=f"Negative score values: {negative_scores}",
    )

    stages = set(
        matches_df["stage"]
        .dropna()
        .astype(str)
        .str.upper()
    )

    unexpected_stages = sorted(
        stages - VALID_STAGES
    )

    report.add(
        name="matches: recognized stages",
        passed=not unexpected_stages,
        details=(
            "All stages are recognized."
            if not unexpected_stages
            else f"Unexpected stages: {unexpected_stages}"
        ),
    )

    durations = set(
        matches_df["duration"]
        .dropna()
        .astype(str)
        .str.upper()
    )

    unexpected_durations = sorted(
        durations - VALID_DURATIONS
    )

    report.add(
        name="matches: recognized durations",
        passed=not unexpected_durations,
        details=(
            "All durations are recognized."
            if not unexpected_durations
            else (
                "Unexpected durations: "
                f"{unexpected_durations}"
            )
        ),
    )


def validate_team_performance(
    performance_df: pd.DataFrame,
    matches_df: pd.DataFrame,
    report: ValidationReport,
) -> None:
    """Validate the team-match performance dataset."""

    required_columns = {
        "team_match_id",
        "match_id",
        "match_date_utc",
        "stage",
        "team_id",
        "team_name",
        "opponent_team_id",
        "opponent_name",
        "venue_side",
        "goals_scored",
        "goals_conceded",
        "goal_difference",
        "result",
        "clean_sheet",
        "team_match_number",
        "cumulative_goal_difference",
    }

    check_required_columns(
        report,
        performance_df,
        "team_match_performance",
        required_columns,
    )

    if not required_columns.issubset(
        performance_df.columns
    ):
        return

    check_non_null(
        report,
        performance_df,
        "team_match_performance",
        [
            "team_match_id",
            "match_id",
            "match_date_utc",
            "stage",
            "team_id",
            "team_name",
            "opponent_team_id",
            "opponent_name",
            "venue_side",
        ],
    )

    report.add(
        name="team performance: expected row count",
        passed=(
            len(performance_df)
            == EXPECTED_TEAM_MATCH_COUNT
        ),
        details=(
            f"Expected {EXPECTED_TEAM_MATCH_COUNT}; "
            f"found {len(performance_df)}."
        ),
    )

    duplicate_ids = int(
        performance_df[
            "team_match_id"
        ].duplicated().sum()
    )

    report.add(
        name="team performance: unique IDs",
        passed=duplicate_ids == 0,
        details=f"Duplicate team-match IDs: {duplicate_ids}",
    )

    rows_per_match = (
        performance_df.groupby("match_id")
        .size()
    )

    invalid_match_groups = int(
        (rows_per_match != 2).sum()
    )

    report.add(
        name="team performance: two rows per match",
        passed=invalid_match_groups == 0,
        details=(
            "Matches without exactly two rows: "
            f"{invalid_match_groups}"
        ),
    )

    valid_match_ids = set(matches_df["match_id"])
    performance_match_ids = set(
        performance_df["match_id"]
    )

    unknown_match_ids = sorted(
        performance_match_ids - valid_match_ids
    )

    report.add(
        name="team performance: valid match references",
        passed=not unknown_match_ids,
        details=(
            "All match IDs reference the matches dataset."
            if not unknown_match_ids
            else f"Unknown match IDs: {unknown_match_ids}"
        ),
    )

    same_opponent_mask = (
        performance_df["team_id"]
        == performance_df["opponent_team_id"]
    )

    report.add(
        name="team performance: team differs from opponent",
        passed=not same_opponent_mask.any(),
        details=(
            "All teams differ from their opponents."
            if not same_opponent_mask.any()
            else (
                "Invalid rows: "
                f"{int(same_opponent_mask.sum())}"
            )
        ),
    )

    venue_values = set(
        performance_df["venue_side"]
        .dropna()
        .astype(str)
    )

    invalid_venues = sorted(
        venue_values - VALID_VENUE_SIDES
    )

    report.add(
        name="team performance: valid venue side",
        passed=not invalid_venues,
        details=(
            "All venue-side values are valid."
            if not invalid_venues
            else f"Invalid values: {invalid_venues}"
        ),
    )

    result_values = set(
        performance_df["result"]
        .dropna()
        .astype(str)
    )

    invalid_results = sorted(
        result_values - VALID_RESULTS
    )

    report.add(
        name="team performance: valid results",
        passed=not invalid_results,
        details=(
            "All result values are valid."
            if not invalid_results
            else f"Invalid values: {invalid_results}"
        ),
    )

    finished_rows = performance_df[
        performance_df["status"] == "FINISHED"
    ].copy()

    finished_null_scores = int(
        finished_rows[
            ["goals_scored", "goals_conceded"]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    report.add(
        name="team performance: finished rows have scores",
        passed=finished_null_scores == 0,
        details=(
            "Finished rows missing scores: "
            f"{finished_null_scores}"
        ),
    )

    numeric_goal_difference = (
        pd.to_numeric(
            finished_rows["goals_scored"],
            errors="coerce",
        )
        - pd.to_numeric(
            finished_rows["goals_conceded"],
            errors="coerce",
        )
    )

    recorded_goal_difference = pd.to_numeric(
        finished_rows["goal_difference"],
        errors="coerce",
    )

    invalid_goal_difference = int(
        (
            numeric_goal_difference
            != recorded_goal_difference
        ).sum()
    )

    report.add(
        name="team performance: correct goal difference",
        passed=invalid_goal_difference == 0,
        details=(
            "Incorrect goal-difference rows: "
            f"{invalid_goal_difference}"
        ),
    )

    expected_clean_sheet = (
        pd.to_numeric(
            finished_rows["goals_conceded"],
            errors="coerce",
        )
        == 0
    )

    recorded_clean_sheet = (
        finished_rows["clean_sheet"]
        .astype(str)
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
    )

    invalid_clean_sheets = int(
        (
            expected_clean_sheet
            != recorded_clean_sheet
        ).sum()
    )

    report.add(
        name="team performance: correct clean sheets",
        passed=invalid_clean_sheets == 0,
        details=(
            "Incorrect clean-sheet rows: "
            f"{invalid_clean_sheets}"
        ),
    )

    selected_found = set(
        performance_df.loc[
            performance_df["team_name"].isin(
                SELECTED_TEAMS
            ),
            "team_name",
        ]
    )

    missing_selected = sorted(
        SELECTED_TEAMS - selected_found
    )

    report.add(
        name="team performance: finalists present",
        passed=not missing_selected,
        details=(
            "Spain and Argentina records are present."
            if not missing_selected
            else f"Missing teams: {missing_selected}"
        ),
    )

    grouped_scores = performance_df.groupby(
        "match_id"
    ).agg(
        total_goals_scored=(
            "goals_scored",
            "sum",
        ),
        total_goals_conceded=(
            "goals_conceded",
            "sum",
        ),
    )

    inconsistent_score_totals = int(
        (
            grouped_scores["total_goals_scored"]
            != grouped_scores["total_goals_conceded"]
        ).sum()
    )

    report.add(
        name="team performance: opposing scores reconcile",
        passed=inconsistent_score_totals == 0,
        details=(
            "Matches with inconsistent perspective totals: "
            f"{inconsistent_score_totals}"
        ),
    )


def save_report(
    report: ValidationReport,
) -> Path:
    """Save the validation report as JSON."""

    VALIDATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        VALIDATION_DIR
        / "validation_report.json"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report.to_dictionary(),
            file,
            indent=2,
        )

    return output_path


def print_report(
    report: ValidationReport,
) -> None:
    """Print the validation results."""

    print("\nValidation results:")

    for check in report.checks:
        symbol = "PASS" if check["passed"] else "FAIL"

        print(
            f"[{symbol}] {check['name']}: "
            f"{check['details']}"
        )

    print(
        "\nOverall validation status: "
        f"{'PASSED' if report.passed else 'FAILED'}"
    )


def main() -> None:
    """Run all processed-data validation checks."""

    print("Starting World Cup dataset validation...")

    teams_df = load_csv("teams.csv")
    matches_df = load_csv("matches.csv")
    performance_df = load_csv(
        "team_match_performance.csv"
    )

    report = ValidationReport()

    validate_teams(
        teams_df,
        report,
    )

    validate_matches(
        matches_df,
        report,
    )

    validate_team_performance(
        performance_df,
        matches_df,
        report,
    )

    report_path = save_report(report)
    print_report(report)

    print(
        "\nValidation report saved to: "
        f"{report_path.relative_to(PROJECT_ROOT)}"
    )

    if not report.passed:
        raise SystemExit(
            "Validation failed. Review the failed checks "
            "before database loading."
        )


if __name__ == "__main__":
    main()