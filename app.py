import pathlib
import webview

HTML_FILE = "circular_outer_halo_oneway.html"  # Pastikan file ini ada di folder yang sama

p = pathlib.Path(__file__).parent / HTML_FILE
if not p.exists():
    raise FileNotFoundError(f"Tidak ditemukan: {p}")

window = webview.create_window(
    title="circular_outer_halo_oneway",
    url=p.as_uri(),
    width=900,
    height=900,
    resizable=False
)
webview.start()