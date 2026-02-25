import json

from app.core.config import get_settings
from app.db.sqlite import init_db
from app.metrics.summary import build_metrics_summary


def main() -> None:
    settings = get_settings()
    init_db(settings.sqlite_path)
    summary = build_metrics_summary(settings.sqlite_path)

    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.reports_dir / "metrics-summary.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
