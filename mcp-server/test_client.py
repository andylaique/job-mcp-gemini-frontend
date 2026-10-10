"""In-memory test of the job-postings MCP server tools."""

import anyio
from mcp import Client

from server import mcp


async def main() -> None:
    async with Client(mcp) as client:
        print("=== list_tools ===")
        tools = await client.list_tools()
        for t in tools.tools:
            print(f"  - {t.name}: {t.description[:80]}...")

        print("\n=== search_postings_by_skill(skill='Python') ===")
        result = await client.call_tool("search_postings_by_skill", {"skill": "Python"})
        print(result.structured_content or result.content)

        print("\n=== count_postings_by_company() ===")
        result = await client.call_tool("count_postings_by_company", {})
        print(result.structured_content or result.content)

        print("\n=== get_job_details(job_id=1) ===")
        result = await client.call_tool("get_job_details", {"job_id": 1})
        print(result.structured_content or result.content)

        print("\n=== Bad input: empty skill ===")
        try:
            await client.call_tool("search_postings_by_skill", {"skill": "   "})
        except Exception as e:
            print(f"  Expected error: {e}")

        print("\n=== Bad input: unknown job_id ===")
        try:
            await client.call_tool("get_job_details", {"job_id": 999})
        except Exception as e:
            print(f"  Expected error: {e}")


if __name__ == "__main__":
    anyio.run(main)
