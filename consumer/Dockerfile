FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

COPY consumer/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer_writer_snmp.py ./consumer_writer_snmp.py
COPY models ./models

ENV PYTHONUNBUFFERED=1

CMD ["python", "consumer_writer_snmp.py"]
