# Use Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose ports
EXPOSE 5000 7860

# Install supervisor to run both servers
RUN apt-get update && apt-get install -y supervisor && mkdir -p /var/log/supervisor

# Add supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Start supervisor
CMD ["supervisord", "-n"]
