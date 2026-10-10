"""
Job Postings MCP Server

Exposes tools over the Model Context Protocol for searching and analyzing
a sample dataset of job postings.

Run with stdio (default for local clients like Claude Desktop / MCP Inspector):
    uv run mcp run server.py

Or over Streamable HTTP (for remote / frontend integration):
    uv run mcp run server.py --transport streamable-http
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from mcp.server import MCPServer

# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.json"


def load_jobs() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Job dataset not found at {DATA_PATH}")
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


JOBS = load_jobs()

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "job-postings",
    version="1.0.0",
    instructions=(
        "You are connected to a job-postings dataset. "
        "Use the available tools to search jobs by skill, count postings by company, "
        "list companies, or get details for a specific job ID. "
        "Always prefer tools over guessing."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_postings_by_skill(
    skill: Annotated[
        str,
        Field(
            description="Skill or technology to search for (case-insensitive partial match). Examples: 'Python', 'React', 'Kubernetes'.",
            min_length=1,
            max_length=64,
        ),
    ],
    remote_only: Annotated[
        bool,
        Field(description="If true, only return remote-friendly postings."),
    ] = False,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of matching postings to return.",
            ge=1,
            le=50,
        ),
    ] = 10,
) -> list[dict[str, Any]]:
    """Search job postings that require a given skill.

    Performs a case-insensitive substring match against each posting's skills list.
    Returns a list of matching postings (id, title, company, location, remote, skills, salary range).
    Raises a clear error if the skill string is empty or invalid.
    """
    skill_clean = skill.strip()
    if not skill_clean:
        raise ValueError(
            "skill must be a non-empty string. Example: skill='Python'"
        )

    skill_lower = skill_clean.lower()
    matches: list[dict[str, Any]] = []

    for job in JOBS:
        job_skills = [s.lower() for s in job.get("skills", [])]
        if any(skill_lower in s or s in skill_lower for s in job_skills):
            if remote_only and not job.get("remote", False):
                continue
            matches.append(
                {
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "remote": job["remote"],
                    "skills": job["skills"],
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                }
            )
            if len(matches) >= limit:
                break

    return matches


@mcp.tool()
def count_postings_by_company(
    company: Annotated[
        str | None,
        Field(
            description=(
                "Optional company name filter (case-insensitive partial match). "
                "If omitted, returns counts for every company in the dataset."
            ),
            max_length=128,
        ),
    ] = None,
) -> dict[str, int]:
    """Count the number of job postings per company.

    When `company` is provided, returns a single-entry dict with the count for that company
    (or 0 if no match). When omitted, returns a dict mapping every company name to its count.
    """
    counts: dict[str, int] = {}
    for job in JOBS:
        name = job["company"]
        counts[name] = counts.get(name, 0) + 1

    if company is not None:
        company_clean = company.strip()
        if not company_clean:
            raise ValueError(
                "company, if provided, must be a non-empty string. "
                "Pass null/omit the argument to get counts for all companies."
            )
        company_lower = company_clean.lower()
        filtered = {
            k: v
            for k, v in counts.items()
            if company_lower in k.lower() or k.lower() in company_lower
        }
        if not filtered:
            return {company_clean: 0}
        return filtered

    return counts


@mcp.tool()
def get_job_details(
    job_id: Annotated[
        int,
        Field(
            description="Numeric ID of the job posting to retrieve.",
            ge=1,
        ),
    ],
) -> dict[str, Any]:
    """Retrieve the full details of a single job posting by its ID.

    Returns title, company, location, remote flag, skills, salary range and description.
    Raises a clear error if the ID does not exist.
    """
    for job in JOBS:
        if job["id"] == job_id:
            return job
    raise ValueError(
        f"No job posting found with id={job_id}. "
        f"Valid IDs range from 1 to {max(j['id'] for j in JOBS)}."
    )


@mcp.tool()
def list_companies() -> list[str]:
    """Return a sorted list of all unique company names present in the dataset."""
    return sorted({job["company"] for job in JOBS})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Default transport is stdio; pass --transport streamable-http for HTTP
    mcp.run()
