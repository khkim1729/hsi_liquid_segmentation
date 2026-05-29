import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import cv2
from PIL import Image
from sklearn.cluster import KMeans
import io

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from lo_parser import LivingOpticsReader

# Paths
lo_filepath = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/data/spectral-detection/liquid-segmentation.lo"
output_dir = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/docs/images"
os.makedirs(output_dir, exist_ok=True)

# Load HSI reader
reader = LivingOpticsReader(lo_filepath)
num_frames = len(reader)
wavelengths = reader.wavelengths

print("Fitting K-Means models (K=4, 5, 6) on Frame 150 where the hand is present...")
frame_150 = reader.get_frame(150)
spectral_150 = frame_150['spectral_data']

kmeans_k4 = KMeans(n_clusters=4, random_state=42, n_init=10).fit(spectral_150)
kmeans_k5 = KMeans(n_clusters=5, random_state=42, n_init=10).fit(spectral_150)
kmeans_k6 = KMeans(n_clusters=6, random_state=42, n_init=10).fit(spectral_150)

# Establish color lists for consistent rendering
k4_colors = ['#34495e', '#bdc3c7', '#2980b9', '#d35400'] # Dark Gray, Light Gray, Blue, Orange
k5_colors = ['#1a252f', '#95a5a6', '#2980b9', '#16a085', '#d35400'] # Deep Gray, Light Gray, Blue, Teal, Orange
k6_colors = ['#1a252f', '#7f8c8d', '#bdc3c7', '#2980b9', '#16a085', '#d35400'] # Deep Gray, Mid Gray, Light Gray, Blue, Teal, Orange

# Define a robust hand contour extractor using OpenCV on the scene_image
def extract_hand_contour(scene_image):
    # Resize for fast image processing
    h, w = scene_image.shape
    resized = cv2.resize(scene_image, (512, 608))
    
    # Threshold to find bright regions (human skin/glove has higher reflectance than the dark background board)
    _, thresh = cv2.threshold(resized, 75, 255, cv2.THRESH_BINARY)
    
    # Apply morphological closing to fill holes in the hand blob
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    hand_contour = None
    max_area = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 2000: # Threshold for hand size
            # Get bounding box to verify it's near the top or sides (where the hand enters)
            x, y, w_box, h_box = cv2.boundingRect(cnt)
            # The tray is in the center, hand is entering from the edges
            if y < 400 or x < 150 or (x + w_box) > 362:
                if area > max_area:
                    max_area = area
                    hand_contour = cnt
                    
    # Scale contour back to original size (2048 x 2432)
    if hand_contour is not None:
        scaled_contour = hand_contour.copy().astype(np.float32)
        scaled_contour[:, 0, 0] = hand_contour[:, 0, 0] * (2048.0 / 512.0)
        scaled_contour[:, 0, 1] = hand_contour[:, 0, 1] * (2432.0 / 608.0)
        return scaled_contour
    return None

# Process every 10th frame for fast compilation
print("\nGenerating hand overlay animations for K=4, K=5, and K=6...")
fig, ax = plt.subplots(figsize=(5.12, 6.08), dpi=100)

for K, k_name, kmeans, colors_list in [
    (4, "k4", kmeans_k4, k4_colors),
    (5, "k5", kmeans_k5, k5_colors),
    (6, "k6", kmeans_k6, k6_colors)
]:
    print(f"\nProcessing K={K} Hand Overlay GIF...")
    gif_frames = []
    
    for f_idx in range(0, num_frames, 10):
        frame = reader.get_frame(f_idx)
        scene_image = frame['scene_image']
        spectral_data = frame['spectral_data']
        coords = frame['coordinates']
        
        # Predict K-Means labels
        pred_labels = kmeans.predict(spectral_data)
        
        ax.clear()
        ax.imshow(scene_image, cmap='gray', extent=[0, 2048, 2432, 0])
        
        # Draw spectral clusters
        for class_id in range(K):
            idx = np.where(pred_labels == class_id)[0]
            # Map class ID to color list cyclically to avoid index error
            color = colors_list[class_id % len(colors_list)]
            ax.scatter(coords[idx, 0], coords[idx, 1], c=color, s=1.5, alpha=0.80, edgecolors='none')
            
        # Segment and draw hand outline contour in glowing red
        hand_cnt = extract_hand_contour(scene_image)
        if hand_cnt is not None:
            # Reshape contour to draw with matplotlib
            pts = hand_cnt.reshape(-1, 2)
            # Close the polygon by appending the first point at the end
            pts = np.vstack([pts, pts[0]])
            ax.plot(pts[:, 0], pts[:, 1], color='#e74c3c', linewidth=2.0, label='Experimenter Hand Outline', zorder=10)
            
        ax.set_title(f'K={K} Segmentation + Hand Overlay | Frame {f_idx:03d}', fontsize=10, fontweight='bold', pad=8)
        ax.set_xlim(0, 2048)
        ax.set_ylim(2432, 0)
        ax.axis('off')
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.02)
        buf.seek(0)
        img = Image.open(buf)
        img.load()
        gif_frames.append(img)
        buf.close()
        
    gif_filename = os.path.join(output_dir, f"liquid_segmentation_{k_name}_hand.gif")
    gif_frames[0].save(
        gif_filename,
        save_all=True,
        append_images=gif_frames[1:],
        duration=100,
        loop=0
    )
    print(f"K={K} Hand Overlay GIF compiled successfully: {gif_filename}")

plt.close(fig)
print("\nAll hand overlay animations generated successfully!")
