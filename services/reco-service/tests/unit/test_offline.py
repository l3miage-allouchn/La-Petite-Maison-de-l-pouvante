"""The offline playground must keep working for the data scientist."""

import sys

import pytest

from app.model import offline


async def test_demo_events_are_valid_and_model_recommends(capsys: pytest.CaptureFixture[str]) -> None:
    events = offline.load_events(offline.DEFAULT_EVENTS)
    assert len(events) > 100

    recommender = await offline.build("cooccurrence", events, offline.DEFAULT_CATALOG)
    items = await recommender.recommend("u-orc-fan", 4)
    assert len(items) == 4

    await offline.evaluate("cooccurrence", events, offline.DEFAULT_CATALOG, 4)
    assert "HitRate@4" in capsys.readouterr().out


@pytest.mark.parametrize("args", [[], ["--user", "u-giallo-fan"], ["--similar", "fig-nosferatu"], ["--evaluate"]])
async def test_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], args: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["offline", *args])
    await offline.main()
    assert "events loaded" in capsys.readouterr().out
