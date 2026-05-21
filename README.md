# SnapTales

Desktop Python app to load photos, crop to square, add a Polaroid i-Type style border and text, then export printer-friendly layouts.

## Run

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python snaptales_app.py
```

## Implemented Workflow

1. Open one image from disk.
2. Crop with draggable square region (move and resize).
3. Convert to Polaroid ratio and textured border based on Task.md dimensions.
4. Add text with 7 font choices, 7 preset colors plus custom color, horizontal/vertical alignment.
5. Preview and save as-is or placed on 10x15 cm / 13x18 cm paper (maximize or original Polaroid size).
