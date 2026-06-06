FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# 1 worker is intentional — do NOT increase it without understanding the consequences:
#   - CalendarContext event cache is per-process; N workers = N independent caches
#     and N x Google Calendar API calls per TTL window.
#   - The streaming pipeline holds a worker thread for the full LLM inference duration
#     (up to 120s). Multiple workers allow concurrent users but each ties up a thread.
# Timeout 120s covers the worst-case STT→LLM→TTS pipeline on slow hardware.
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]