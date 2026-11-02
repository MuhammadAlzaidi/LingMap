"""Offline smoke tests for the LingMap rendering engine."""
import pandas as pd
import pytest
import matplotlib.pyplot as plt
import geopandas as gpd
import lingmap_core as core

def test_reject_invalid_coordinates():
    with pytest.raises(ValueError):
        core.validate_locations(pd.DataFrame([{
            "country":"Jordan","city":"Amman","latitude":100,"longitude":35
        }]))

def test_remove_unsubstantiated_metadata():
    df=pd.read_csv(core.ROOT/"data"/"cities.csv")
    assert "speakers" not in df.columns
    assert "dialect" not in df.columns

def test_english_grayscale_exports(monkeypatch):
    # Tests run without downloading Natural Earth.
    shapes=gpd.read_file(core.ROOT/"data"/"arab_countries.geojson")
    monkeypatch.setattr(core,"boundaries",lambda:shapes.rename(columns={"name":"country"}))
    data=pd.DataFrame([{"country":"Saudi Arabia","city":"Riyadh",
                        "latitude":24.7136,"longitude":46.6753},
                       {"country":"Saudi Arabia","city":"Makkah",
                        "latitude":21.3891,"longitude":39.8579}])
    fig=core.make_figure(data,["Saudi Arabia"],
                         roles={"Riyadh":"Data collection site",
                                "Makkah":"Comparison site"},
                         width_mm=85,show_context=False)
    assert core.export_figure(fig,"png",300).startswith(b"\x89PNG")
    assert core.export_figure(fig,"pdf").startswith(b"%PDF")
    assert b"<svg" in core.export_figure(fig,"svg")
    plt.close(fig)
