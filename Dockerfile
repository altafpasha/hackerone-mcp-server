FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY h1_mcp_server.py .

CMD ["python", "h1_mcp_server.py"]
