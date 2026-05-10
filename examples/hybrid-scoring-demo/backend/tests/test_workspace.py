import pytest

from app.services.workspace import create_widget, list_widgets, remove_widget, reorder_widgets


@pytest.mark.asyncio
async def test_create_and_list_workspace_widget(db):
    widget = await create_widget(
        db,
        widget_type="ranking_list",
        title="Top scored records",
        source_tool="get_scored_records",
        data={"records": [{"title": "One", "fit": 0.9}]},
    )

    widgets = await list_widgets(db)

    assert widgets[0]["id"] == widget["id"]
    assert widgets[0]["widget_type"] == "ranking_list"
    assert widgets[0]["position"] == 0


@pytest.mark.asyncio
async def test_reject_unknown_widget_type(db):
    with pytest.raises(Exception, match="unknown widget_type"):
        await create_widget(
            db,
            widget_type="money_flow",
            title="Money flow",
            source_tool="get_scored_records",
            data={"records": [{"title": "One"}]},
        )


@pytest.mark.asyncio
async def test_reject_incompatible_source_tool_widget_type(db):
    with pytest.raises(Exception, match="cannot be rendered"):
        await create_widget(
            db,
            widget_type="run_history_list",
            title="Wrong widget",
            source_tool="get_scored_records",
            data={"records": [{"title": "One"}]},
        )


@pytest.mark.asyncio
async def test_reject_empty_widget_data(db):
    with pytest.raises(Exception, match="must not be empty"):
        await create_widget(
            db,
            widget_type="ranking_list",
            title="Empty",
            source_tool="get_scored_records",
            data={},
        )


@pytest.mark.asyncio
async def test_remove_widget_persists(db):
    widget = await create_widget(
        db,
        widget_type="summary_card",
        title="Score result",
        source_tool="score_records",
        data={"scores_written": 3, "rescore": False},
    )

    result = await remove_widget(db, widget["id"])

    assert result["removed"] is True
    assert await list_widgets(db) == []


@pytest.mark.asyncio
async def test_reorder_widgets(db):
    first = await create_widget(
        db,
        widget_type="summary_card",
        title="Score result",
        source_tool="score_records",
        data={"scores_written": 3, "rescore": False},
    )
    second = await create_widget(
        db,
        widget_type="ranking_list",
        title="Top scored records",
        source_tool="get_scored_records",
        data={"records": [{"title": "One", "fit": 0.9}]},
    )

    result = await reorder_widgets(db, [second["id"], first["id"]])

    assert result["reordered"] is True
    widgets = await list_widgets(db)
    assert [widget["id"] for widget in widgets] == [second["id"], first["id"]]


@pytest.mark.asyncio
async def test_reorder_rejects_omitted_widget(db):
    first = await create_widget(
        db,
        widget_type="summary_card",
        title="Score result",
        source_tool="score_records",
        data={"scores_written": 3, "rescore": False},
    )
    await create_widget(
        db,
        widget_type="ranking_list",
        title="Top scored records",
        source_tool="get_scored_records",
        data={"records": [{"title": "One", "fit": 0.9}]},
    )

    with pytest.raises(Exception, match="missing widget ids"):
        await reorder_widgets(db, [first["id"]])
