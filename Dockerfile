FROM python:3.9-slim AS builder

WORKDIR /app

RUN groupadd -g 3000 app && useradd -m -u 10001 -g 3000 --no-log-init app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

RUN apt-get purge -y --auto-remove build-essential

FROM python:3.9-slim

WORKDIR /app

RUN groupadd -g 3000 app && useradd -m -u 10001 -g 3000 --no-log-init app

COPY --from=builder /install /usr/local

COPY . /app

RUN chown -R app:app /app

USER app

EXPOSE 8000

ENV CLUSTER_NAME="gke-us"
ENV SERVICE_B_URL="http://consumer:8000/" 

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
