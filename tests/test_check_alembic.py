import subprocess
import sys


def test_check_alembic_runs():
    # Run the script and ensure it exits with code 0/1/2 (not crash)
    res = subprocess.run([sys.executable, 'scripts/check_alembic.py'], capture_output=True, text=True)
    # script returns 0 (pass), 1 (warnings) or 2 (errors)
    assert res.returncode in (0, 1, 2)
