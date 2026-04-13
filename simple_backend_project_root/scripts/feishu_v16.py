#!/usr/bin/env python
"""Write leads to Feishu table v16"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Setup path
root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root / "backend"))
os.chdir(str(root))

# Add simple_backend to path
sys.path.insert(0, str(root / "simple_backend"))
import output


async def main():
    # Load leads
    leads_path = root / "simple_backend/data/output/leads_20260412_182200.json"
    with open(leads_path, "r") as f:
        leads = json.load(f)

    print(f"Loaded {len(leads)} leads")

    # Create new table v16
    print("Creating table v16...")
    result = await output.create_feishu_table(table_name="外贸获客结果v16")
    print(f"Result: {result}")

    # Get the new table ID
    if "data" in result:
        table_id = result["data"].get("table", {}).get("table_id")
        print(f"Created table_id: {table_id}")

        # Write records
        if table_id:
            print(f"Writing {len(leads)} leads to table...")
            write_result = await output.write_feishu(leads, table_id=table_id)
            print(f"Write result: {write_result}")
    elif "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Unknown result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
