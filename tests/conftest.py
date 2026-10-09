import pytest


@pytest.fixture(autouse=True)
def _own_photo_folder(tmp_path, monkeypatch):
    """Tests never touch the real ~/.local/share/beranda/photos folder."""
    monkeypatch.setenv("BERANDA_PHOTOS", str(tmp_path / "beranda-photos"))
