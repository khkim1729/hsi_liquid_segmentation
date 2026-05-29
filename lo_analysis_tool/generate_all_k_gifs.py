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

# Load reader
reader = LivingOpticsReader(lo_filepath)
num_frames = len(reader)
wavelengths = reader.wavelengths

print("Fitting K-Means models on Frame 0 for K=2, 4, and 5...")
frame_0 = reader.get_frame(0)
spectral_0 = frame_0['spectral_data']
coords = frame_0['coordinates']

# Train K-Means
kmeans_k2 = KMeans(n_clusters=2, random_state=42, n_init=10).fit(spectral_0)
kmeans_k4 = KMeans(n_clusters=4, random_state=42, n_init=10).fit(spectral_0)
kmeans_k5 = KMeans(n_clusters=5, random_state=42, n_init=10).fit(spectral_0)

# Consistency mappings
# Let's inspect K=2: usually Background vs Liquid (determined by reflectance)
k2_means = [np.mean(spectral_0[kmeans_k2.labels_ == i]) for i in range(2)]
bg_k2 = np.argmin(k2_means)
liq_k2 = 1 - bg_k2
k2_map = {bg_k2: 0, liq_k2: 1} # 0=Background (gray), 1=Liquid (blue)
k2_colors = ['#7f8c8d', '#2980b9']

# Inspect K=4: Background shadow, Bright surface, Aqueous, Organic
# Sort by average reflectance to separate low-albedo (backgrounds) from high-albedo (liquids)
k4_means = [np.mean(spectral_0[kmeans_k4.labels_ == i], axis=0) for i in range(4)]
k4_avg_refl = [np.mean(m) for m in k4_means]
sorted_k4 = np.argsort(k4_avg_refl) # low reflectance to high reflectance

# 0=Shadow (dark gray), 1=Surface (light gray), and check NIR dip for the remaining two
idx_830 = np.argmin(np.abs(wavelengths - 831.0))
idx_788 = np.argmin(np.abs(wavelengths - 788.0))
water_dip_k4 = [k4_means[i][idx_830] / (k4_means[i][idx_788] + 1e-9) for i in range(4)]

liq_rem = sorted_k4[2:]
if water_dip_k4[liq_rem[0]] < water_dip_k4[liq_rem[1]]:
    aq_k4 = liq_rem[0]
    org_k4 = liq_rem[1]
else:
    aq_k4 = liq_rem[1]
    org_k4 = liq_rem[0]

k4_map = {
    sorted_k4[0]: 0, # Background Shadow
    sorted_k4[1]: 1, # Background Surface
    aq_k4: 2,        # Aqueous Liquid
    org_k4: 3        # Organic Liquid
}
k4_colors = ['#34495e', '#bdc3c7', '#2980b9', '#d35400'] # Dark Gray, Light Gray, Blue, Orange

# Inspect K=5: detailed subdivisions
k5_means = [np.mean(spectral_0[kmeans_k5.labels_ == i], axis=0) for i in range(5)]
k5_avg_refl = [np.mean(m) for m in k5_means]
sorted_k5 = np.argsort(k5_avg_refl)

# 0=Deep Shadow, 1=Bright Surface, check others for liquids and mixtures
water_dip_k5 = [k5_means[i][idx_830] / (k5_means[i][idx_788] + 1e-9) for i in range(5)]

# Sort the remaining 3 clusters by water dip ratio
liq_rem_k5 = sorted_k5[2:]
dip_sorted = np.argsort([water_dip_k5[i] for i in liq_rem_k5])

k5_map = {
    sorted_k5[0]: 0,               # Deep Shadow
    sorted_k5[1]: 1,               # Surface
    liq_rem_k5[dip_sorted[0]]: 2,  # Aqueous Core (strongest dip)
    liq_rem_k5[dip_sorted[1]]: 3,  # Liquid Interface/Mixing (moderate dip)
    liq_rem_k5[dip_sorted[2]]: 4   # Organic Liquid (no dip)
}
k5_colors = ['#1a252f', '#95a5a6', '#2980b9', '#16a085', '#d35400'] # Very dark, Gray, Ocean Blue, Teal, Orange

# Process sequence every 10th frame for speed
print("\nGenerating animation frames for K=2, 4, 5 (every 10th frame)...")

fig, ax = plt.subplots(figsize=(5.12, 6.08), dpi=100)

for K, k_name, kmeans, k_map, colors_list in [
    (2, "k2", kmeans_k2, k2_map, k2_colors),
    (4, "k4", kmeans_k4, k4_map, k4_colors),
    (5, "k5", kmeans_k5, k5_map, k5_colors)
]:
    print(f"Rendering K={K} dynamic animation...")
    gif_frames = []
    
    for f_idx in range(0, num_frames, 10):
        frame = reader.get_frame(f_idx)
        scene_image = frame['scene_image']
        spectral_data = frame['spectral_data']
        coords = frame['coordinates']
        
        # Predict consistently
        pred_raw = kmeans.predict(spectral_data)
        pred_std = np.array([k_map[lbl] for lbl in pred_raw])
        
        ax.clear()
        ax.imshow(scene_image, cmap='gray', extent=[0, 2048, 2432, 0])
        
        for class_id in range(K):
            idx = np.where(pred_std == class_id)[0]
            ax.scatter(coords[idx, 0], coords[idx, 1], c=colors_list[class_id], s=1.5, alpha=0.85, edgecolors='none')
            
        ax.set_title(f'Spectral Segmentation (K={K}) | Frame {f_idx:03d}', fontsize=11, fontweight='bold', pad=8)
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
        
    gif_filename = os.path.join(output_dir, f"liquid_segmentation_{k_name}_fast.gif")
    gif_frames[0].save(
        gif_filename,
        save_all=True,
        append_images=gif_frames[1:],
        duration=100,
        loop=0
    )
    print(f"K={K} GIF compiled successfully at: {gif_filename}")

plt.close(fig)
print("\nAll K-Means alternative animations generated successfully!")
