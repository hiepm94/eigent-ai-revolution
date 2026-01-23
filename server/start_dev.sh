docker compose up -d
nohup chromium-browser --remote-debugging-port=9222 --no-first-run --no-default-browser-check> /dev/null 2>&1 &
