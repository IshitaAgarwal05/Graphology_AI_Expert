
import json
import io
import numpy as np
import cv2
import streamlit as st
from PIL import Image
from utils.image_processing import (
    load_image_cv, binarize, deskew, estimate_xheight, components_from_bw,
    median_slant_deg, baseline_slope_deg, median_word_gap, avg_stroke_width_estimate,
    loop_ratio, margins_pixels
)
from utils.graphology import interpret_traits

st.set_page_config(page_title="Handwriting Traits Analyzer (Graphology-style)", layout="wide")

st.title("✍️ Handwriting Traits Analyzer (Graphology-style)")
st.caption("Disclaimer: This app extracts **objective handwriting features** (slant, spacing, baseline, etc.) and maps them to common **graphology conventions** for fun/education. It is **not** a psychological test.")

with st.sidebar:
    st.header("Upload")
    up = st.file_uploader("Upload a handwriting image (PNG/JPG)", type=["png", "jpg", "jpeg"])
    st.markdown("---")
    st.header("Preprocessing")
    blur = st.checkbox("Gaussian blur (3×3)", value=True)
    invert = st.checkbox("Invert foreground/background automatically", value=True)
    do_deskew = st.checkbox("Deskew document", value=True)
    st.markdown("---")
    st.header("Feature Options")
    sample_step = st.slider("Column sampling step for baseline fit", 1, 10, 5)
    gap_norm_by = st.selectbox("Normalize word gaps by", ["x-height (median char height)", "image width"])

    st.markdown("---")
    st.write("Made with ❤️ in Streamlit")

col1, col2 = st.columns([1,1])

if up is None:
    st.info("Upload a handwriting image to begin.")
    st.stop()

# Read
img = load_image_cv(up)
orig_vis = img.copy()

# Binarize
bw, used_inversion = binarize(img, auto_invert=invert, blur=blur)

# Deskew
angle_deg = 0.0
if do_deskew:
    bw, angle_deg = deskew(bw)

# Compute components
comps = components_from_bw(bw)

# Objective features
xheight = estimate_xheight(comps)
slant_deg = median_slant_deg(comps)
baseline_deg = baseline_slope_deg(bw, step=sample_step)
gap_med, gaps = median_word_gap(bw)
if gap_norm_by == "x-height (median char height)":
    gap_norm = (gap_med / max(1.0, xheight)) if gap_med is not None and xheight not in (None, 0) else None
else:
    gap_norm = (gap_med / bw.shape[1]) if gap_med is not None else None

stroke_w = avg_stroke_width_estimate(bw)
loop_frac = loop_ratio(bw)
margins = margins_pixels(bw)

features = {
    "deskew_angle_deg": float(angle_deg),
    "median_slant_deg": None if slant_deg is None else float(slant_deg),
    "baseline_slope_deg": float(baseline_deg),
    "xheight_px": None if xheight is None else float(xheight),
    "median_word_gap_px": None if gap_med is None else float(gap_med),
    "normalized_word_gap": None if gap_norm is None else float(gap_norm),
    "avg_stroke_width_px": float(stroke_w),
    "loop_ratio": float(loop_frac),
    "margins_px": {k:int(v) for k,v in margins.items()},
    "image_size": {"h": int(bw.shape[0]), "w": int(bw.shape[1])}
}

# Interpret
interpretation = interpret_traits(features)

with col1:
    st.subheader("Input & Binarized View")
    st.image(cv2.cvtColor(orig_vis, cv2.COLOR_BGR2RGB), caption="Original", use_column_width=True)
    st.image(bw, caption=f"Binarized (deskew angle: {angle_deg:.2f}°)", use_column_width=True, clamp=True)

with col2:
    st.subheader("Extracted Features")
    st.json(features)
    st.subheader("Graphology-style Interpretation")
    st.write(interpretation)

# Download JSON
buf = io.BytesIO()
buf.write(json.dumps({"features": features, "interpretation": interpretation}, indent=2).encode("utf-8"))
buf.seek(0)
st.download_button("⬇️ Download results (JSON)", data=buf, file_name="handwriting_traits.json", mime="application/json")
