FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .

# Install without cache to keep image small
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces requires running as non-root user (id 1000)
RUN useradd -m -u 1000 user
USER user

EXPOSE 7860

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]