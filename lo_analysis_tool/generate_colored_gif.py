import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from sklearn.cluster import KMeans
import io

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from lo_parser import LivingOpticsReader

# Paths
lo_filepath = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/data/spectral-detection/liquid-segmentation.lo"
output_dir = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/docs/images"
os.makedirs(output_dir, exist_ok=True)

# 1. Load HSI data reader
reader = LivingOpticsReader(lo_filepath)
num_frames = len(reader)
wavelengths = reader.wavelengths
print(f"Loaded LO dataset with {num_frames} frames. wavelengths range: {wavelengths[0]:.1f}nm to {wavelengths[-1]:.1f}nm")

# 2. Fit K-Means on Frame 0 once to determine centroids consistently
print("Training base K-Means model on Frame 0...")
frame_0 = reader.get_frame(0)
spectral_0 = frame_0['spectral_data']
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
labels_0 = kmeans.fit(spectral_0)

# Determine mapping to standard labels (0: Background, 1: Aqueous, 2: Organic)
cluster_means = [np.mean(spectral_0[labels_0.labels_ == i], axis=0) for i in range(3)]
avg_reflectance = [np.mean(m) for m in cluster_means]

# Map 830nm vs 788nm water dip ratio
idx_830 = np.argmin(np.abs(wavelengths - 831.0))
idx_788 = np.argmin(np.abs(wavelengths - 788.0))
water_dip_ratio = [m[idx_830] / (m[idx_788] + 1e-9) for m in cluster_means]

sorted_by_refl = np.argsort(avg_reflectance)
bg_cluster = sorted_by_refl[0]
rem_clusters = sorted_by_refl[1:]

if water_dip_ratio[rem_clusters[0]] < water_dip_ratio[rem_clusters[1]]:
    aqueous_cluster = rem_clusters[0]
    organic_cluster = rem_clusters[1]
else:
    aqueous_cluster = rem_clusters[1]
    organic_cluster = rem_clusters[0]

# Class mappings: keys are original cluster IDs, values are standard IDs
id_mapping = {
    bg_cluster: 0,
    aqueous_cluster: 1,
    organic_cluster: 2
}
print(f"Centroids mapped consistently: Background={bg_cluster} -> 0, Aqueous={aqueous_cluster} -> 1, Organic={organic_cluster} -> 2")

# 3. Generate color-coded segmentation animation GIF
print("\nGenerating color-coded spectral segmentation frames (every 5th frame)...")
gif_frames = []
colors = ['#7f8c8d', '#2980b9', '#d35400'] # Gray, Blue, Orange
class_names = ["Background", "Aqueous Liquid", "Organic Liquid"]

# To avoid memory leaks and make compilation faster, we pre-configure a matplotlib figure
fig, ax = plt.subplots(figsize=(5.12, 6.08), dpi=100)

for f_idx in range(0, num_frames, 5):
    frame = reader.get_frame(f_idx)
    scene_image = frame['scene_image']
    spectral_data = frame['spectral_data']
    coords = frame['coordinates']
    
    # Predict labels using base K-Means centroids
    pred_raw_labels = kmeans.predict(spectral_data)
    pred_std_labels = np.array([id_mapping[lbl] for lbl in pred_raw_labels])
    
    # Draw frame
    ax.clear()
    ax.imshow(scene_image, cmap='gray', extent=[0, 2048, 2432, 0])
    
    for class_id in range(3):
        idx = np.where(pred_std_labels == class_id)[0]
        ax.scatter(coords[idx, 0], coords[idx, 1], c=colors[class_id], s=1.5, alpha=0.85, edgecolors='none')
        
    ax.set_title(f'Spectral Segmentation | Frame {f_idx:03d}', fontsize=11, fontweight='bold', pad=8)
    ax.set_xlim(0, 2048)
    ax.set_ylim(2432, 0)
    ax.axis('off') # Hide axes to make the GIF clean
    
    # Convert matplotlib figure to PIL Image in-memory
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.02)
    buf.seek(0)
    img = Image.open(buf)
    img.load() # Load image data into memory before closing buffer
    gif_frames.append(img)
    buf.close()
    
    if (f_idx + 5) % 50 == 0 or f_idx == num_frames - 1:
        print(f"Rendered segmentation frame {f_idx + 1}/{num_frames}")

plt.close(fig)

# Save the GIF
if gif_frames:
    gif_filename = os.path.join(output_dir, "liquid_segmentation_colored_fast.gif")
    print(f"\nCompiling animated GIF: {gif_filename}...")
    gif_frames[0].save(
        gif_filename,
        save_all=True,
        append_images=gif_frames[1:],
        duration=100,
        loop=0
    )
    print("Color-coded animated GIF compiled successfully!")
else:
    print("Error: No frames generated.")
