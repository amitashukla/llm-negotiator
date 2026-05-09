FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p /app/data

# Fail the image build if routes are missing (catches stale/wrong copies).
RUN python -c "from app.main import API_BUILD_ID, app; paths=[getattr(r,'path',None) for r in app.routes]; assert '/api/health' in paths and '/docs' in paths, (API_BUILD_ID, paths)"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
