import pytest


@pytest.mark.asyncio
async def test_workspace_widget_route_flow(client):
    create = await client.post(
        "/workspace/widgets",
        json={
            "widget_type": "summary_card",
            "title": "Score result",
            "source_tool": "score_records",
            "data": {"scores_written": 3, "rescore": False},
        },
    )
    assert create.status_code == 200
    widget_id = create.json()["widget"]["id"]

    listed = await client.get("/workspace/widgets")
    assert listed.status_code == 200
    assert listed.json()["widgets"][0]["id"] == widget_id

    removed = await client.delete(f"/workspace/widgets/{widget_id}")
    assert removed.status_code == 200
    assert removed.json()["removed"] is True

    listed_again = await client.get("/workspace/widgets")
    assert listed_again.json()["widgets"] == []


@pytest.mark.asyncio
async def test_workspace_rejects_invalid_widget(client):
    response = await client.post(
        "/workspace/widgets",
        json={
            "widget_type": "run_history_list",
            "title": "Bad",
            "source_tool": "get_scored_records",
            "data": {"records": [{"title": "One"}]},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "incompatible_widget"


@pytest.mark.asyncio
async def test_workspace_reorder_route(client):
    first = await client.post(
        "/workspace/widgets",
        json={
            "widget_type": "summary_card",
            "title": "Score result",
            "source_tool": "score_records",
            "data": {"scores_written": 3, "rescore": False},
        },
    )
    second = await client.post(
        "/workspace/widgets",
        json={
            "widget_type": "ranking_list",
            "title": "Top scored records",
            "source_tool": "get_scored_records",
            "data": {"records": [{"title": "One", "fit": 0.9}]},
        },
    )

    response = await client.post(
        "/workspace/widgets/reorder",
        json={"widget_ids": [second.json()["widget"]["id"], first.json()["widget"]["id"]]},
    )

    assert response.status_code == 200
    assert [widget["id"] for widget in response.json()["widgets"]] == [
        second.json()["widget"]["id"],
        first.json()["widget"]["id"],
    ]
