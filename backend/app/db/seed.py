import os
import sys

_curr_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(os.path.dirname(_curr_dir))
_repo_dir = os.path.dirname(_backend_dir)
for _d in [_repo_dir, _backend_dir]:
    if _d not in sys.path:
        sys.path.insert(0, _d)

try:
    from backend.app.database.seed import seed_database
except ImportError:
    from app.database.seed import seed_database

if __name__ == "__main__":
    seed_database()
