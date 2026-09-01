import argparse
import asyncio
import os
from dotenv import load_dotenv
from agents.workflow import run_pipeline
from utils.sentry import init_sentry
load_dotenv(override=True)
init_sentry()
def main():
    parser = argparse.ArgumentParser(
        description="Run the AI News Aggregator pipeline."
    )
    parser.add_argument(
        "--user_id",
        type=str,
        default=None,
        help="Run the digest only for this user.",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run_pipeline(user_id=args.user_id))
    except Exception as exc:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
        raise
if __name__ == "__main__":
    main()