from fastapi.testclient import TestClient

from backend.server import app


client = TestClient(app)


def test_memory_create_list_delete_flow():
    create_response = client.post(
        "/memory",
        json={"content": "用户喜欢被叫阿泽", "category": "preference", "importance": 2},
    )
    assert create_response.status_code == 200

    list_response = client.get("/memory")
    assert list_response.status_code == 200
    memories = list_response.json()
    assert any(item["content"] == "用户喜欢被叫阿泽" for item in memories)

    memory_id = next(item["id"] for item in memories if item["content"] == "用户喜欢被叫阿泽")
    delete_response = client.delete(f"/memory/{memory_id}")
    assert delete_response.status_code == 200
