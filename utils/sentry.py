import os
import sentry_sdk


def init_sentry() -> None:
    """
    Initialize Sentry only when SENTRY_DSN is configured.
    Safe to call from both FastAPI and the pipeline.
    """
    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        print("⚠️ SENTRY_DSN not configured — Sentry disabled")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(
            os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")
        ),
        send_default_pii=False,
    )

    print("✅ Sentry initialized")