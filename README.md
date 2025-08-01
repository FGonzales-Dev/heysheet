# HeySheet

A full-stack application with Django backend, React frontend, and PostgreSQL database, all running in Docker.

## Setup and Running

1. **Prerequisites**: Ensure you have Docker and Docker Compose installed on your system.

2. **Build and Run**:
   ```bash
   docker-compose up --build
   ```

3. **Access the Application**:
   - Frontend: [http://localhost:5173](http://localhost:5173)
   - Backend API: [http://localhost:8000](http://localhost:8000)
   - Admin Interface: [http://localhost:8000/admin](http://localhost:8000/admin)

4. **Database Migrations**:
   After starting the containers, run migrations:
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

5. **Creating a Superuser**:
   To access the Django admin interface, create a superuser:
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

6. **Stopping the Application**:
   ```bash
   docker-compose down
   ```

## Development

- **Backend**: Django project is in the `backend` directory. Make changes there for API development.
- **Frontend**: React project with Vite is in the `frontend` directory. Make UI changes there.

## Notes

- The frontend is configured to proxy API requests to the backend at `/api`.
- CORS is configured to allow requests from the frontend at `http://localhost:5173`. 