FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

VOLUME ["/data"]

EXPOSE 9000

CMD ["python", "-u", "server.py"]
