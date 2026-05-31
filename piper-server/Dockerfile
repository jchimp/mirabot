FROM python:3.12-slim

RUN pip install --no-cache-dir flask piper-tts

WORKDIR /app
COPY server.py .

EXPOSE 5000

CMD ["python", "server.py"]