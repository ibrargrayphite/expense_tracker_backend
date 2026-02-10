# XPENSE Tracker API Documentation

## API Documentation URLs

Once the Django server is running, you can access the API documentation at:

### Swagger UI (Interactive)
**URL:** http://localhost:8000/api/docs/

The Swagger UI provides an interactive interface where you can:
- Browse all available API endpoints
- Test API calls directly from the browser
- View request/response schemas
- Authenticate using JWT tokens

### ReDoc (Alternative Documentation)
**URL:** http://localhost:8000/api/redoc/

ReDoc provides a clean, three-panel documentation interface.

### OpenAPI Schema (JSON)
**URL:** http://localhost:8000/api/schema/

Raw OpenAPI 3.0 schema in JSON format.

---

## Authentication

The API uses JWT (JSON Web Token) authentication.

### Getting Tokens

**Endpoint:** `POST /api/token/`

**Request Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Refreshing Tokens

**Endpoint:** `POST /api/token/refresh/`

**Request Body:**
```json
{
  "refresh": "your_refresh_token"
}
```

### Using Authentication in Swagger

1. Click the **"Authorize"** button at the top of the Swagger UI
2. Enter your token in the format: `Bearer <your_access_token>`
3. Click "Authorize"
4. All subsequent requests will include the authentication header

---

## API Endpoints Overview

### Users
- `POST /api/users/` - Register a new user
- `GET /api/users/` - List all users (authenticated)
- `GET /api/users/{id}/` - Get user details
- `PUT /api/users/{id}/` - Update user
- `PATCH /api/users/{id}/` - Partially update user
- `DELETE /api/users/{id}/` - Delete user

### Accounts
- `GET /api/accounts/` - List all accounts
- `POST /api/accounts/` - Create a new account
- `GET /api/accounts/{id}/` - Get account details
- `PUT /api/accounts/{id}/` - Update account
- `PATCH /api/accounts/{id}/` - Partially update account
- `DELETE /api/accounts/{id}/` - Delete account

### Loans
- `GET /api/loans/` - List all loans
- `POST /api/loans/` - Create a new loan record
- `GET /api/loans/{id}/` - Get loan details
- `PUT /api/loans/{id}/` - Update loan
- `PATCH /api/loans/{id}/` - Partially update loan
- `DELETE /api/loans/{id}/` - Delete loan

### Transactions
- `GET /api/transactions/` - List all transactions
- `POST /api/transactions/` - Create a new transaction
- `GET /api/transactions/{id}/` - Get transaction details
- `PUT /api/transactions/{id}/` - Update transaction
- `PATCH /api/transactions/{id}/` - Partially update transaction
- `DELETE /api/transactions/{id}/` - Delete transaction

---

## Quick Start

1. **Start the backend server:**
   ```bash
   cd backend
   source /home/muhammad/Desktop/venvs/expense_tracker/bin/activate
   python manage.py runserver
   ```

2. **Access Swagger UI:**
   Open http://localhost:8000/api/docs/ in your browser

3. **Register a user:**
   - Use the `POST /api/users/` endpoint
   - No authentication required for registration

4. **Get authentication token:**
   - Use the `POST /api/token/` endpoint
   - Provide your username and password

5. **Authorize in Swagger:**
   - Click "Authorize" button
   - Enter: `Bearer <your_access_token>`

6. **Start making API calls!**

---

## Notes

- All endpoints (except user registration and token endpoints) require authentication
- The API automatically filters data by the authenticated user
- Creating transactions automatically updates account balances and loan amounts
- Deleting transactions reverses the balance/loan updates
