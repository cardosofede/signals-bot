# Use an official Python runtime as a parent image
FROM python:3.10

# Set the working directory in the container
WORKDIR /usr/src/app

# Install Poetry
RUN pip install poetry

# Copy the project files into the container
COPY pyproject.toml poetry.lock* /usr/src/app/

# Disable virtualenvs created by Poetry
# as the Docker container itself provides isolation
RUN poetry config virtualenvs.create false

# Install project dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy the rest of your application's code
COPY . /usr/src/app

# Run the bot when the container launches
CMD ["python", "main.py"]
