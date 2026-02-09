FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True
ENV APP_HOME=/app
WORKDIR $APP_HOME

# Copy necessary files
COPY app.py ./
COPY end_to_end.py ./
COPY pyproject.toml ./
COPY core ./core
COPY templates ./templates

COPY data ./data

# Create utils symlink to core/utils for import compatibility
RUN ln -s core/utils utils

# Install dependencies
RUN pip install --no-cache-dir .

# Run with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
