FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
COPY cc.py .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "cc.py"]