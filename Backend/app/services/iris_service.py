import cv2
import numpy as np
from iris_model.IrisRecognition.src.utils.imgutils import segment, normalize  # <-- code you pasted
from scipy.spatial.distance import hamming

def encode_iris(polar_array, noise):
    """
    Convert normalized iris into binary code + mask.
    """
    # simple quantization (placeholder: use Log-Gabor in production)
    code = (polar_array > 0.5).astype(np.uint8)
    mask = noise.astype(np.uint8)   # 1 = noisy, 0 = valid
    return code, mask

def masked_hamming_distance(code1, mask1, code2, mask2, max_shift=8):
    best = 1.0
    best_shift = 0

    for s in range(-max_shift, max_shift+1):
        c2 = np.roll(code2, shift=s, axis=1)
        m2 = np.roll(mask2, shift=s, axis=1)

        valid = (1 - mask1) * (1 - m2)
        denom = np.sum(valid)
        if denom == 0:
            continue

        diff = (code1 ^ c2) * valid
        hd = diff.sum() / denom

        if hd < best:
            best = hd
            best_shift = s

    return best, best_shift

def extract_iris_features(image_path: str):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Failed to load image.")

    ciriris, cirpupil, _ = segment(img)

    polar_array, noise = normalize(
        img,
        ciriris[1], ciriris[0], ciriris[2],
        cirpupil[1], cirpupil[0], cirpupil[2],
        radpixels=64,
        angulardiv=256
    )

    code, mask = encode_iris(polar_array, noise)
    return code, mask 

def match_iris(features1, features2, threshold=0.36):
    code1, mask1 = features1
    code2, mask2 = features2

    d, shift = masked_hamming_distance(code1, mask1, code2, mask2)
    return {
        "distance": float(d),
        "is_match": bool(d < threshold),
        "best_shift": shift
    }