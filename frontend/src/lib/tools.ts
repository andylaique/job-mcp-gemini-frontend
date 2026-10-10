import jobsData from "./jobs.json";

export type Job = {
  id: number;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  skills: string[];
  salary_min: number;
  salary_max: number;
  description: string;
};

const JOBS = jobsData as Job[];

export function searchPostingsBySkill(
  skill: string,
  remoteOnly = false,
  limit = 10
): Job[] {
  const skillClean = skill.trim();
  if (!skillClean) {
    throw new Error("skill must be a non-empty string. Example: skill='Python'");
  }
  const skillLower = skillClean.toLowerCase();
  const matches: Job[] = [];
  for (const job of JOBS) {
    const jobSkills = job.skills.map((s) => s.toLowerCase());
    if (jobSkills.some((s) => skillLower.includes(s) || s.includes(skillLower))) {
      if (remoteOnly && !job.remote) continue;
      matches.push(job);
      if (matches.length >= limit) break;
    }
  }
  return matches;
}

export function countPostingsByCompany(company?: string | null): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const job of JOBS) {
    counts[job.company] = (counts[job.company] || 0) + 1;
  }
  if (company != null) {
    const companyClean = company.trim();
    if (!companyClean) {
      throw new Error(
        "company, if provided, must be a non-empty string. Pass null/omit to get all counts."
      );
    }
    const companyLower = companyClean.toLowerCase();
    const filtered: Record<string, number> = {};
    for (const [k, v] of Object.entries(counts)) {
      if (companyLower.includes(k.toLowerCase()) || k.toLowerCase().includes(companyLower)) {
        filtered[k] = v;
      }
    }
    if (Object.keys(filtered).length === 0) return { [companyClean]: 0 };
    return filtered;
  }
  return counts;
}

export function getJobDetails(jobId: number): Job {
  const job = JOBS.find((j) => j.id === jobId);
  if (!job) {
    const maxId = Math.max(...JOBS.map((j) => j.id));
    throw new Error(
      `No job posting found with id=${jobId}. Valid IDs range from 1 to ${maxId}.`
    );
  }
  return job;
}

export function listCompanies(): string[] {
  return [...new Set(JOBS.map((j) => j.company))].sort();
}

/** Gemini function declarations that mirror the MCP tools */
export const geminiTools = [
  {
    name: "search_postings_by_skill",
    description:
      "Search job postings that require a given skill. Case-insensitive partial match against the skills list. Returns matching postings.",
    parameters: {
      type: "object",
      properties: {
        skill: {
          type: "string",
          description:
            "Skill or technology to search for (case-insensitive). Examples: 'Python', 'React', 'Kubernetes'.",
        },
        remote_only: {
          type: "boolean",
          description: "If true, only return remote-friendly postings.",
        },
        limit: {
          type: "integer",
          description: "Maximum number of matching postings to return (1-50).",
        },
      },
      required: ["skill"],
    },
  },
  {
    name: "count_postings_by_company",
    description:
      "Count the number of job postings per company. Optionally filter by company name (partial match).",
    parameters: {
      type: "object",
      properties: {
        company: {
          type: "string",
          description:
            "Optional company name filter (case-insensitive partial match). Omit to get counts for every company.",
        },
      },
    },
  },
  {
    name: "get_job_details",
    description:
      "Retrieve the full details of a single job posting by its numeric ID.",
    parameters: {
      type: "object",
      properties: {
        job_id: {
          type: "integer",
          description: "Numeric ID of the job posting (starting from 1).",
        },
      },
      required: ["job_id"],
    },
  },
  {
    name: "list_companies",
    description: "Return a sorted list of all unique company names in the dataset.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
];

export function executeTool(
  name: string,
  args: Record<string, unknown>
): unknown {
  switch (name) {
    case "search_postings_by_skill":
      return searchPostingsBySkill(
        String(args.skill ?? ""),
        Boolean(args.remote_only),
        typeof args.limit === "number" ? args.limit : 10
      );
    case "count_postings_by_company":
      return countPostingsByCompany(
        args.company == null ? null : String(args.company)
      );
    case "get_job_details":
      return getJobDetails(Number(args.job_id));
    case "list_companies":
      return listCompanies();
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}
