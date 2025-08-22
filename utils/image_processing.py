
import cv2
import numpy as np
from sklearn.linear_model import LinearRegression

def load_image_cv(file_obj):
    data = file_obj.read()
    img_arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    return img

def binarize(img, auto_invert=True, blur=True):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim==3 else img.copy()
    if blur:
        g = cv2.GaussianBlur(g, (3,3), 0)
    # Otsu on normal and inverted, pick higher foreground coverage when auto_invert
    _, bw1 = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    _, bw2 = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    if auto_invert:
        if bw1.sum() > bw2.sum():
            return bw1, True
        else:
            return (255-bw2), False  # ensure foreground==255
    else:
        return bw1, True

def deskew(bw):
    # Expect bw with foreground=255 on background=0
    coords = np.column_stack(np.where(bw>0))
    if coords.shape[0] < 20:
        return bw, 0.0
    rect = cv2.minAreaRect(coords.astype(np.float32))
    angle = rect[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = bw.shape
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    rotated = cv2.warpAffine(bw, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, float(angle)

def components_from_bw(bw, min_area=15):
    num, labels, stats, centroids = cv2.connectedComponentsWithStats((bw>0).astype(np.uint8), connectivity=8)
    comps = []
    for i in range(1, num):
        x,y,w,h,area = stats[i]
        if area < min_area: 
            continue
        mask = (labels==i).astype(np.uint8)
        comps.append({"bbox":(x,y,w,h), "area":int(area), "centroid":tuple(centroids[i]), "mask":mask})
    return comps

def _pca_slant(component_mask):
    ys, xs = np.where(component_mask>0)
    if xs.size < 8:
        return None
    pts = np.column_stack([xs, ys]).astype(np.float32)
    mean, eigvecs = cv2.PCACompute(pts, mean=None)[:2]
    vx, vy = eigvecs[0]
    angle = np.degrees(np.arctan2(vy, vx))  # relative to +x
    # Slant: relative to vertical (90 deg ~ upright)
    return angle - 90.0

def median_slant_deg(comps):
    vals = []
    for c in comps:
        ang = _pca_slant(c["mask"])
        if ang is not None:
            # Normalize to [-90,90] for stability
            a = ((ang + 180) % 180) - 90
            vals.append(a)
    if not vals:
        return None
    return float(np.median(vals))

def baseline_slope_deg(bw, step=5):
    xs, ys = [], []
    H, W = bw.shape
    for x in range(0, W, max(1,int(step))):
        col = np.where(bw[:, x]>0)[0]
        if col.size>0:
            xs.append(x); ys.append(col.max())
    if len(xs) < 10:
        return 0.0
    X = np.array(xs).reshape(-1,1)
    y = np.array(ys).astype(np.float32)
    lr = LinearRegression().fit(X, y)
    slope = lr.coef_[0]
    # image y increases downward -> invert sign to match "ascending positive"
    return float(-np.degrees(np.arctan(slope)))

def estimate_xheight(comps):
    if not comps: 
        return None
    heights = [c["bbox"][3] for c in comps]
    return float(np.median(heights))

def median_word_gap(bw):
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours]
    if not boxes:
        return None, []
    # Sort by line-ish: y then x
    boxes.sort(key=lambda b:(b[1], b[0]))
    gaps = []
    for i in range(len(boxes)-1):
        x,y,w,h = boxes[i]
        x2,y2,w2,h2 = boxes[i+1]
        # same line? vertical overlap >= 40% of min height
        vo = min(y+h, y2+h2)-max(y, y2)
        if vo >= 0.4*min(h,h2):
            gap = x2 - (x+w)
            if gap > 0:
                gaps.append(gap)
    if not gaps:
        return None, []
    return float(np.median(gaps)), gaps

def avg_stroke_width_estimate(bw):
    # Distance transform on foreground gives radius to background.
    # Approx average stroke width ≈ 2 * mean distance over foreground.
    # Ensure foreground=255
    f = (bw>0).astype(np.uint8)
    if f.sum() == 0:
        return 0.0
    dist = cv2.distanceTransform(f, cv2.DIST_L2, 3)
    mean_rad = dist[f>0].mean() if (f>0).any() else 0.0
    return float(2.0*mean_rad)

def loop_ratio(bw):
    # Use contour hierarchy to count holes
    cnts, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None or len(cnts)==0:
        return 0.0
    hier = hier[0]
    holes = 0
    parents = 0
    for i,(nx,pr,ch,pt) in enumerate(hier):
        # parent contour has child => loop area inside
        if ch != -1:
            parents += 1
            # count number of children
            j = ch
            while j != -1:
                holes += 1
                j = hier[j][0]
    if parents == 0:
        return 0.0
    return float(holes / max(1, parents))

def margins_pixels(bw):
    # simple whitespace bands
    rows = (bw>0).any(axis=1)
    cols = (bw>0).any(axis=0)
    top = int(np.argmax(rows)) if rows.any() else 0
    bottom = int(len(rows) - np.argmax(rows[::-1]) - 1) if rows.any() else bw.shape[0]-1
    left = int(np.argmax(cols)) if cols.any() else 0
    right = int(len(cols) - np.argmax(cols[::-1]) - 1) if cols.any() else bw.shape[1]-1
    return {"top": top, "left": left, "right": bw.shape[1]-1-right, "bottom": bw.shape[0]-1-bottom}
