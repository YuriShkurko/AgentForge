import pytest


@pytest.mark.asyncio
async def test_seed_lists_projects_and_tasks(client):
    seed = await client.post("/seed")
    assert seed.status_code == 200
    assert seed.json()["created_projects"] == 2

    projects = await client.get("/projects")
    assert projects.status_code == 200
    assert len(projects.json()) == 2

    tasks = await client.get("/tasks")
    assert tasks.status_code == 200
    assert len(tasks.json()) >= 5


@pytest.mark.asyncio
async def test_create_update_task_and_add_note(client):
    await client.post("/seed")
    project = (await client.get("/projects")).json()[0]

    created = await client.post("/tasks", json={
        "project_id": project["id"],
        "title": "Write project workspace tests",
        "priority": "high",
        "owner": "Dev",
    })
    assert created.status_code == 200
    task = created.json()

    updated = await client.patch(f"/tasks/{task['id']}", json={"status": "done"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"

    note = await client.post(f"/projects/{project['id']}/notes", json={"body": "Validated deterministic project flow.", "task_id": task["id"]})
    assert note.status_code == 200
    assert note.json()["event_type"] == "note_added"

    activity = await client.get("/activity")
    assert activity.status_code == 200
    assert any(item["event_type"] == "note_added" for item in activity.json())
