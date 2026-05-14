FROM python:3.10-slim
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

COPY producer/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY snmp_producer.py ./snmp_producer.py
COPY inventory.csv ./inventory.csv

ENV PYTHONUNBUFFERED=1

CMD ["python", "snmp_producer.py"]
