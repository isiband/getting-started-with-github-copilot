import copy
import pytest
from fastapi.testclient import TestClient

from src.app import app, activities

# capture initial state for resetting between tests
_original_activities = copy.deepcopy(activities)

@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activities dict before each test."""
    activities.clear()
    activities.update(copy.deepcopy(_original_activities))
    yield

@pytest.fixture
def client():
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)

# -------------------------
# GET / and /activities
# -------------------------

def test_root_redirect(client):
    # Arrange - nothing special
    # Act (don't follow redirects so we can inspect status)
    response = client.get("/", follow_redirects=False)
    # Assert
    assert response.status_code in (307, 308)
    assert response.headers["location"].endswith("/static/index.html")


def test_get_activities_returns_all(client):
    # Arrange
    # Act
    response = client.get("/activities")
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # original activities should match keys
    assert set(data.keys()) == set(_original_activities.keys())

# -------------------------
# POST signup tests
# -------------------------

def test_signup_success(client):
    # Arrange
    activity = "Chess Club"
    email = "newstudent@mergington.edu"
    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})
    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity}"
    assert email in activities[activity]["participants"]


def test_signup_nonexistent_activity(client):
    # Arrange
    activity = "Nonexistent"
    email = "someone@mergington.edu"
    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})
    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_duplicate_email(client):
    # Arrange
    activity = "Chess Club"
    email = _original_activities[activity]["participants"][0]
    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})
    # Assert
    assert response.status_code == 400
    assert "already signed up" in response.json()["detail"]


def test_signup_at_capacity(client):
    # Arrange
    activity = "Small Class"
    # create a tiny activity for capacity testing
    activities[activity] = {
        "description": "Tiny",
        "schedule": "Now",
        "max_participants": 1,
        "participants": ["first@mergington.edu"],
    }
    email = "second@mergington.edu"
    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})
    # Assert
    assert response.status_code == 400
    assert "full" in response.json()["detail"]

# -------------------------
# DELETE unregister tests
# -------------------------

def test_unregister_success(client):
    # Arrange
    activity = "Chess Club"
    email = _original_activities[activity]["participants"][0]
    # Act
    response = client.delete(f"/activities/{activity}/participants/{email}")
    # Assert
    assert response.status_code == 200
    assert email not in activities[activity]["participants"]


def test_unregister_nonexistent_activity(client):
    # Arrange
    activity = "Nope"
    email = "nobody@mergington.edu"
    # Act
    response = client.delete(f"/activities/{activity}/participants/{email}")
    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_not_signed_up(client):
    # Arrange
    activity = "Chess Club"
    email = "absent@mergington.edu"
    # Act
    response = client.delete(f"/activities/{activity}/participants/{email}")
    # Assert
    assert response.status_code == 404
    assert "not signed up" in response.json()["detail"]

# -------------------------
# Edge-case lifecycle
# -------------------------

def test_signup_then_unregister(client):
    # Arrange
    activity = "Tennis Club"
    email = "cycle@mergington.edu"
    # Act
    signup_resp = client.post(f"/activities/{activity}/signup", params={"email": email})
    del_resp = client.delete(f"/activities/{activity}/participants/{email}")
    # Assert
    assert signup_resp.status_code == 200
    assert del_resp.status_code == 200
    assert email not in activities[activity]["participants"]
