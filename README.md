
# Handwriting Traits Analyzer (Graphology-style)

This Streamlit app extracts **objective handwriting features** from an uploaded image (slant, baseline slope, spacing, letter size, loop ratio, margins, and a pressure proxy) and maps them to **graphology-style interpretations**. It’s for fun/education — not a psychological test.

## Features
- Binarization, optional deskew
- Component analysis (x-height, slant via PCA)
- Baseline slope (linear regression on lower envelope)
- Word spacing (median gap), normalized by x-height or image width
- Stroke width proxy via distance transform
- Loop ratio using contour hierarchy
- Margin measurements
- JSON export of all features + interpretation

## Project Structure
```
graphology_streamlit/
├── app.py
├── utils/
│   ├── image_processing.py
│   └── graphology.py
├── assets/
│   └── (put sample images here)
├── requirements.txt
└── README.md
```

## Setup & Run

```bash
# 1) Create venv (recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the app
streamlit run app.py
```

### [Graphology AI Expert Working Link](https://graphology-ai-expert-ia.streamlit.app/).

## Notes
- The "pressure" metric uses **average stroke width** as a proxy, which depends on image resolution. Try to upload similar DPI scans for fair comparisons.
- Thresholds are heuristic; you can tweak them in `utils/graphology.py`.
- This app doesn’t perform OCR; it focuses on visual traits rather than text content.
