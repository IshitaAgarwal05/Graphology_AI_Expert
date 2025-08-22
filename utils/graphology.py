
def _bucket(value, low, high, low_label, mid_label, high_label):
    if value is None:
        return "unknown"
    if value < low: return low_label
    if value > high: return high_label
    return mid_label

def interpret_traits(feats: dict) -> str:
    sl = feats.get("median_slant_deg", None)
    gap = feats.get("normalized_word_gap", None)
    base = feats.get("baseline_slope_deg", 0.0)
    stroke = feats.get("avg_stroke_width_px", 0.0)
    loop_r = feats.get("loop_ratio", 0.0)
    margins = feats.get("margins_px", {})
    xh = feats.get("xheight_px", None)

    # Interpretations (graphology-style, heuristic)
    slant_label = "right-slanted (expressive/open)" if (sl is not None and sl > 7) else                   ("left-slanted (reserved/cautious)" if (sl is not None and sl < -7) else "upright (balanced/logical)")

    # Gap normalization assumptions
    if gap is None:
        spacing_label = "unknown spacing"
    else:
        # If normalized by x-height, ~0.4..0.8 is typical
        spacing_label = _bucket(gap, 0.4, 0.8, "narrow (seeks closeness)", "balanced", "wide (values space/independence)")

    baseline_label = "ascending (optimistic/ambitious)" if base > 2 else                      ("descending (tired/discouraged)" if base < -2 else "straight (stable/self-controlled)")

    # Stroke width as proxy for pressure: rough thresholds; depends on resolution
    pressure_label = _bucket(stroke, 1.0, 3.0, "light (sensitive/easygoing)", "medium", "heavy (intense/determined)")

    loops_label = "many loops (imaginative/expressive)" if loop_r > 0.6 else                   ("few loops (reserved/controlled)" if loop_r < 0.2 else "some loops (balanced)")

    # Margins
    left_m = margins.get("left", 0); right_m = margins.get("right", 0)
    if left_m - right_m > 15:
        margin_label = "wide left margin (cautious with past; seeks control)"
    elif right_m - left_m > 15:
        margin_label = "wide right margin (forward-looking/adventurous)"
    else:
        margin_label = "balanced margins"

    size_label = "unknown size"
    if xh is not None:
        size_label = "large letters (outgoing/confident)" if xh > 30 else                      ("small letters (focused/introverted)" if xh < 12 else "medium size (balanced)")

    # Build explanation
    parts = [
        f"• **Slant**: {slant_label}",
        f"• **Spacing**: {spacing_label}",
        f"• **Baseline**: {baseline_label}",
        f"• **Pressure (stroke width proxy)**: {pressure_label}",
        f"• **Loops**: {loops_label}",
        f"• **Margins**: {margin_label}",
        f"• **Letter size**: {size_label}",
        "",
        "_Note: These are heuristic interpretations based on graphology conventions; not diagnostic._"
    ]
    return "\n".join(parts)
