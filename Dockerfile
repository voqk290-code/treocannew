FROM python:3.10-slim
WORKDIR /app
COPY requi.txt .
RUN pip install --no-cache-dir -r requi.txt
COPY . .
CMD ["python", "spamcannew.py"]
