FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HELPMEFINDTHEJOB_DATA_DIR=/app/data
ENV HELPMEFINDTHEJOB_HOST=0.0.0.0
ENV HELPMEFINDTHEJOB_PORT=8765

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py mcp_server.py ./
COPY company_discovery ./company_discovery
COPY static ./static
COPY docs ./docs

RUN mkdir -p /app/data

EXPOSE 8765
VOLUME ["/app/data"]

CMD ["python", "app.py"]
