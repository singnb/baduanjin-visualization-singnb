### Test
```bash
# Move to test directory
cd pi-service\app\tests

# Activate virtual environment (in my localhost as example)
conda activate C:\Users\singn\.conda\envs\mmpose_env

# Install testing packages
pip install pytest pytest-asyncio pytest-mock httpx pytest-cov

# Capture both stdout and stderr with examples
pytest {testFilename} -v > reports\{testReportFilename} 2>&1
pytest .\routers\test_pi_live.py -v --disable-warnings > reports\test_routers.txt 2>&1

```