# Use tiangolo/uwsgi-nginx-flask as the base image
FROM tiangolo/uwsgi-nginx-flask:python3.8

# Copy your Flask app into the image
COPY ./docs /app

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt