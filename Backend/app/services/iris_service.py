import cv2
import numpy as np
from iris_model.IrisRecognition.src.utils.imgutils import segment, normalize  # <-- code you pasted
from scipy.spatial.distance import hamming

def extract_iris_features(image_path: str):
    """
    Full pipeline: segment, normalize, and extract iris template.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Failed to load image.")

    # Step 1: Segment iris
    ciriris, cirpupil, imwithnoise = segment(img)

    # Step 2: Normalize iris (unwrap into polar array)
    polar_array, noise = normalize(
        img,
        ciriris[1], ciriris[0], ciriris[2],  # iris x,y,r
        cirpupil[1], cirpupil[0], cirpupil[2],  # pupil x,y,r
        radpixels=64,
        angulardiv=256
    )

    # Step 3: Flatten as feature vector (basic placeholder)
    features = polar_array.flatten().tolist()
    return features

def match_iris(features1, features2, threshold=0.35):
    """
    Compare two iris templates with Hamming distance.
    """
    # convert to numpy arrays
    arr1, arr2 = np.array(features1), np.array(features2)
    dist = hamming(arr1, arr2)
    return {"distance": float(dist), "is_match": dist < threshold}