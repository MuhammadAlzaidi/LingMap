import pandas as pd
import pytest
import matplotlib.pyplot as plt
from lingmap_core import validate_locations, make_figure, export_figure

def test_bad_coordinates():
    with pytest.raises(ValueError):
        validate_locations(pd.DataFrame([{"country":"Jordan","city":"Amman","latitude":100,"longitude":35}]))

def test_exports():
    data = pd.DataFrame([{"country":"Saudi Arabia","city":"Riyadh","latitude":24.7136,"longitude":46.6753}])
    fig = make_figure(data, ["Saudi Arabia"])
    assert export_figure(fig,"png",300).startswith(b"\x89PNG")
    assert export_figure(fig,"pdf").startswith(b"%PDF")
    assert b"<svg" in export_figure(fig,"svg")
    plt.close(fig)
