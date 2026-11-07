# Testing a FastAPI Application

This guide will help you set up and run tests for your FastAPI application using **pytest** and **HTTPX**, covering basics, databases, authentication, and reusable fixtures.

## 1. Setup and Installation

Install the required testing and database dependencies:

```bash
pip install pytest httpx sqlalchemy
```

* **pytest**: The framework used to write and execute the tests.
* **httpx**: Required by FastAPI's `TestClient` to simulate HTTP requests.
* **sqlalchemy**: Used for managing the application and test databases.

---

## 2. Project Structure

A clean layout keeps your application code separate from your tests:

```text
my_project/
├── database.py      # Main database configuration
├── main.py          # Your FastAPI application and routes
├── conftest.py      # Global test configurations and fixtures
└── test_main.py     # Your test cases
```

---

## 3. Basic Test Example

`TestClient` allows you to test routes instantly without spinning up a live Uvicorn server.

### `main.py`

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello World"}
```

### `test_main.py`

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
```

---

## 4. Pytest Fixtures (`conftest.py`)

Fixtures are reusable setup and teardown blocks. Creating a `conftest.py` file allows `pytest` to share these fixtures automatically across all your test files.

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Provides a clean TestClient instance for every test."""
    with TestClient(app) as c:
        yield c
```

You can now pass `client` as an argument directly into your tests without importing it:

```python
# test_main.py
def test_with_fixture(client):
    response = client.get("/")
    assert response.status_code == 200
```

---

## 5. Testing Databases (SQLAlchemy)

To prevent your tests from polluting or deleting production data, override your FastAPI database dependency to use a separate, temporary test database (like an in-memory SQLite database).

```python
# conftest.py (Add database setups)
import pytest
from sqlalchemy import create_index, create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app

# Use an in-memory SQLite database for fast isolated tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Creates tables before each test and drops them afterward."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provides an isolated database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Overrides the app's get_db dependency with the test database session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    # Clean up the override after the test finishes
    del app.dependency_overrides[get_db]
```

---

## 6. Testing Authentication & Tokens

When testing endpoints protected by security dependencies (like OAuth2 / JWT tokens), you can pass an `Authorization` header directly into your requests.

### Testing a Protected Route

```python
def test_protected_route_without_token(client):
    # Should fail because no credentials were provided
    response = client.get("/users/me")
    assert response.status_code == 401


def test_protected_route_with_token(client):
    # 1. Simulate logging in or generate a mock token
    login_response = client.post(
        "/token", data={"username": "testuser", "password": "password123"}
    )
    token = login_response.json()["access_token"]

    # 2. Pass the token inside the headers
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
```

### Alternative: Overriding the Auth Dependency Entirely

If you want to skip generating a real token entirely during testing, you can mock your current user dependency inside your test file:

```python
from main import get_current_user


def test_admin_dashboard_with_mocked_user(client):
    # Mocking what the dependency returns
    app.dependency_overrides[get_current_user] = lambda: {
        "username": "mockadmin",
        "role": "admin",
    }

    response = client.get("/admin/dashboard")
    assert response.status_code == 200

    # Clean up
    del app.dependency_overrides[get_current_user]
```

---

## 7. How to Run the Tests

Open your terminal in the project's root directory and run:

```bash
# Run all tests
pytest

# Run tests with detailed output (shows individual test names)
pytest -v

# Run tests and stop immediately at the first failure
pytest -x

# Run individual test file
pytest test_main.py

# Rin individual test function
pytest test_main.py::test_read_root

# Runs test_login, test_login_fail, etc.
pytest -k "login" 

# Runs login tests but skips any containing the word "admin"
pytest -k "login and not admin"
```

---

## 8. Tips for Beginners

* **The `test_` Prefix**: Every test function and file name **must** start with `test_` (e.g., `test_auth.py` and `def test_login()`), or `pytest` won't run them.
* **No Server Running**: Do **not** run `uvicorn` while running your tests. `TestClient` manages everything natively.
* **Isolation**: Every test should run completely independently. Relying on the output or state of a previous test will break your suite as it grows.
