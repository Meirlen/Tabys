from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_news():
    response = client.get("/news/")
    print(f"GET /news status: {response.status_code}")
    print(f"GET /news content: {response.json()}")
    assert response.status_code == 200

def test_post_news_no_auth():
    response = client.post("/news/", json={
        "title": "Test News",
        "description": "Test Description",
        "content_text": "Test Content"
    })
    print(f"POST /news (no auth) status: {response.status_code}")
    assert response.status_code == 403 or response.status_code == 401

if __name__ == "__main__":
    try:
        test_get_news()
        test_post_news_no_auth()
        print("Verification successful!")
    except Exception as e:
        print(f"Verification failed: {e}")
