FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot4.py .
COPY data.json .

CMD ["python", "bot4.py"]