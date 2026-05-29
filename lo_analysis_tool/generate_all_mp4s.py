import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import cv2
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

print("Fitting K-Means models (K=2, 4) on Frame 150...")
frame_150 = reader.get_frame(150)
spectral_150 = frame_150['spectral_data']

kmeans_k2 = KMeans(n_clusters=2, random_state=42, n_init=10).fit(spectral_150)
kmeans_k4 = KMeans(n_clusters=4, random_state=42, n_init=10).fit(spectral_150)

# Colors
k2_colors = ['#34495e', '#2980b9']  # Dark Gray, Blue
k4_colors = ['#34495e', '#bdc3c7', '#2980b9', '#d35400']  # Dark Gray, Light Gray, Blue, Orange

# Hand contour helper
def extract_hand_contour(scene_image):
    resized = cv2.resize(scene_image, (512, 608))
    _, thresh = cv2.threshold(resized, 75, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    hand_contour = None
    max_area = 0
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 2000:
            x, y, w_box, h_box = cv2.boundingRect(cnt)
            if y < 400 or x < 150 or (x + w_box) > 362:
                if area > max_area:
                    max_area = area
                    hand_contour = cnt
                    
    if hand_contour is not None:
        scaled_contour = hand_contour.copy().astype(np.float32)
        scaled_contour[:, 0, 0] = hand_contour[:, 0, 0] * (2048.0 / 512.0)
        scaled_contour[:, 0, 1] = hand_contour[:, 0, 1] * (2432.0 / 608.0)
        return scaled_contour
    return None

# Video compiling function
def compile_mp4(K, kmeans, colors_list, overlay_hand, filename):
    video_path = os.path.join(output_dir, filename)
    print(f"Generating: {video_path} (K={K}, Hand Overlay={overlay_hand})")
    
    # Establish video writer details
    # We will use standard 10 FPS for video playback (which matches the 5x fast gif temporal scale)
    fps = 10
    
    # We will grab a single frame to define shape
    fig, ax = plt.subplots(figsize=(5.12, 6.08), dpi=100)
    
    # Pre-determine frame width/height by rendering one dummy frame
    ax.clear()
    ax.imshow(np.zeros((608, 512)), cmap='gray')
    ax.axis('off')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.02)
    buf.seek(0)
    img_arr = cv2.imdecode(np.frombuffer(buf.read(), np.uint8), cv2.IMREAD_COLOR)
    h_frame, w_frame, _ = img_arr.shape
    buf.close()
    
    # Initialize OpenCV VideoWriter with standard H.264 MP4V codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(video_path, fourcc, fps, (w_frame, h_frame))
    
    # We process every 5th frame for a smooth, high-fidelity MP4 video (instead of every 10th frame)
    for f_idx in range(0, num_frames, 5):
        frame = reader.get_frame(f_idx)
        scene_image = frame['scene_image']
        spectral_data = frame['spectral_data']
        coords = frame['coordinates']
        
        pred_labels = kmeans.predict(spectral_data)
        
        ax.clear()
        ax.imshow(scene_image, cmap='gray', extent=[0, 2048, 2432, 0])
        
        for class_id in range(K):
            idx = np.where(pred_labels == class_id)[0]
            color = colors_list[class_id % len(colors_list)]
            ax.scatter(coords[idx, 0], coords[idx, 1], c=color, s=1.5, alpha=0.85, edgecolors='none')
            
        if overlay_hand:
            hand_cnt = extract_hand_contour(scene_image)
            if hand_cnt is not None:
                pts = hand_cnt.reshape(-1, 2)
                pts = np.vstack([pts, pts[0]])
                ax.plot(pts[:, 0], pts[:, 1], color='#e74c3c', linewidth=2.0, zorder=10)
                
        ax.set_title(f'K={K} Segmentation{" + Hand Outline" if overlay_hand else ""} | Frame {f_idx:03d}', fontsize=10, fontweight='bold', pad=8)
        ax.set_xlim(0, 2048)
        ax.set_ylim(2432, 0)
        ax.axis('off')
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.02)
        buf.seek(0)
        # Convert Matplotlib PNG to BGR OpenCV image
        frame_img = cv2.imdecode(np.frombuffer(buf.read(), np.uint8), cv2.IMREAD_COLOR)
        # Ensure it fits the dimensions
        frame_img_resized = cv2.resize(frame_img, (w_frame, h_frame))
        video_writer.write(frame_img_resized)
        buf.close()
        
    video_writer.release()
    plt.close(fig)
    print(f"MP4 Video saved successfully: {video_path}")

# Run compilation
compile_mp4(2, kmeans_k2, k2_colors, False, "liquid_segmentation_k2_fast.mp4")
compile_mp4(4, kmeans_k4, k4_colors, False, "liquid_segmentation_k4_fast.mp4")
compile_mp4(4, kmeans_k4, k4_colors, True, "liquid_segmentation_k4_hand.mp4")

print("\nAll requested MP4 videos compiled successfully!")
