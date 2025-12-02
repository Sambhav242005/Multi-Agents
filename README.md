# HackWave 2.0

HackWave 2.0 is a containerized web application with a Next.js frontend and a FastAPI backend, orchestrated using Docker Compose and Nginx.

## Project Structure

- **backend/**: Contains the FastAPI application, Python source code, and Dockerfile.
- **frontend/**: Contains the Next.js application and Dockerfile.
- **nginx/**: Contains the Nginx configuration for reverse proxying.
- **docker-compose.yml**: Orchestration file for defining and running the services.

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Getting Started

1. **Clone the repository** (if you haven't already):

    ```bash
    git clone <repository-url>
    cd HackWave2.0
    ```

2. **Environment Configuration**:
    - Ensure you have a `.env` file in the `backend/` directory.
    - You can copy the example file:

      ```bash
      cp backend/.env.example backend/.env
      ```

    - Update `backend/.env` with your API keys and configuration.

3. **Run with Docker Compose**:

    ```bash
    docker-compose up --build
    ```

    - The `--build` flag ensures images are rebuilt if there are changes.
    - Add `-d` to run in detached mode (background).

4. **Access the Application**:
    - **Frontend**: Open [http://localhost](http://localhost) in your browser.
    - **Backend API**: Accessible internally via Nginx at `http://localhost/api`.
    - **API Documentation**: [http://localhost/api/docs](http://localhost/api/docs) (if enabled in FastAPI).

## Development

- **Backend**: Located in `backend/`. The Docker container mounts the code, but for hot-reloading in Docker, ensure `uvicorn` is running with `--reload` (configured in `run.py`).
- **Frontend**: Located in `frontend/`.
- **Nginx**: Configuration in `nginx/nginx.conf`.

## Troubleshooting

- **Port Conflicts**: Ensure ports `80` (Nginx), `3000` (Frontend), and `8000` (Backend) are not in use.
- **Logs**: View logs with `docker-compose logs -f`.
