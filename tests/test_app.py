"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) == 9
    
    def test_get_activities_contains_required_fields(self, client):
        """Test that each activity contains required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
    
    def test_get_activities_participants_is_list(self, client):
        """Test that participants field is a list"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_details in data.values():
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant_success(self, client, reset_activities):
        """Test successfully signing up a new participant"""
        email = "new.student@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was added
        assert email in activities[activity]["participants"]
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signing up for non-existent activity"""
        response = client.post(
            "/activities/NonExistent/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant_fails(self, client, reset_activities):
        """Test that duplicate signup is rejected"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity = "Chess Club"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_multiple_participants(self, client, reset_activities):
        """Test signing up multiple participants"""
        activity = "Art Club"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all participants were added
        for email in emails:
            assert email in activities[activity]["participants"]


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant_success(self, client, reset_activities):
        """Test successfully unregistering an existing participant"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity = "Chess Club"
        
        initial_count = len(activities[activity]["participants"])
        
        response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        assert email not in activities[activity]["participants"]
        assert len(activities[activity]["participants"]) == initial_count - 1
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregistering from non-existent activity"""
        response = client.post(
            "/activities/NonExistent/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_non_participant_fails(self, client, reset_activities):
        """Test that unregistering non-participant fails"""
        email = "not.registered@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_then_signup_again(self, client, reset_activities):
        """Test unregistering and then signing up again"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Unregister
        response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Sign up again
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities[activity]["participants"]


class TestSignupAndUnregisterIntegration:
    """Integration tests for signup and unregister workflows"""
    
    def test_full_participant_lifecycle(self, client, reset_activities):
        """Test full lifecycle: signup, verify, unregister, verify"""
        email = "lifecycle@mergington.edu"
        activity = "Programming Class"
        
        # Initially not registered
        assert email not in activities[activity]["participants"]
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Unregister
        response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email not in activities[activity]["participants"]
    
    def test_multiple_activities_signup(self, client, reset_activities):
        """Test signing up for multiple activities"""
        email = "multi.student@mergington.edu"
        activities_to_join = ["Chess Club", "Drama Club", "Science Club"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify signup for all activities
        for activity in activities_to_join:
            assert email in activities[activity]["participants"]
        
        # Unregister from one activity
        response = client.post(
            f"/activities/{activities_to_join[0]}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify still in other activities
        assert email not in activities[activities_to_join[0]]["participants"]
        assert email in activities[activities_to_join[1]]["participants"]
        assert email in activities[activities_to_join[2]]["participants"]
    
    def test_special_characters_in_email(self, client, reset_activities):
        """Test handling emails with special characters"""
        email = "student+test@mergington.edu"
        activity = "Basketball Club"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert email in activities[activity]["participants"]
