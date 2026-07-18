import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.custom_logger import get_recent_logs

logs = get_recent_logs(limit=5)
for log in logs:
    print(json.dumps(log, default=str, indent=2))
