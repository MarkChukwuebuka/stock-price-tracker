FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv and compile dependencies
RUN pip install --upgrade pip
COPY Pipfile Pipfile.lock /app/
RUN pip install pipenv && pipenv install --system --deploy

# Copy the current directory contents into the container at /app
COPY . /app/

# Expose the port Django is running on
EXPOSE 8050

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "spt.wsgi:application"]
