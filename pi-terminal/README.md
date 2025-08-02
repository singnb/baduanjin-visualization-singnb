```bash
cd tests

pip install pytest pytest-asyncio pytest-mock httpx pytest-env

# From the tests directory:
pytest test_main.py -v --disable-warnings > reports/test_main.txt 2>&1
pytest test_api_routes.py -v --disable-warnings > reports/test_api_routers.txt 2>&1
pytest test_websocket_handlers.py -v --disable-warnings > reports/test_webscoket.txt 2>&1
pytest test_config.py -v --disable-warnings > reports/test_config.txt 2>&1
pytest test_analyzer.py -v --disable-warnings > reports/test_analyzer.txt 2>&1

pytest test_analyzer_integration.py -v --disable-warnings > reports/test_analyzer_integration.txt 2>&1
pytest test_baduanjin_tracker.py -v --disable-warnings > reports/test_baduanjin_tracker.txt 2>&1

pytest test_video_converter.py -v --disable-warnings > reports/test_video_converter.txt 2>&1

```
