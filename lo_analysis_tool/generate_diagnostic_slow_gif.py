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

# 1. Initialize Reader and Fit Base K-Means
reader = LivingOpticsReader(lo_filepath)
num_frames = len(reader)
wavelengths = reader.wavelengths

print("Fitting baseline K-Means (K=3) on Frame 0...")
frame_0 = reader.get_frame(0)
spectral_0 = frame_0['spectral_data']
coords_0 = frame_0['coordinates']

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10).fit(spectral_0)
labels_0 = kmeans.labels_

# Standardize labels
cluster_means = [np.mean(spectral_0[labels_0 == i], axis=0) for i in range(3)]
avg_reflectance = [np.mean(m) for m in cluster_means]
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

id_mapping = {bg_cluster: 0, aqueous_cluster: 1, organic_cluster: 2}

# Re-mapped labels for Frame 0
std_labels_0 = np.array([id_mapping[lbl] for lbl in labels_0])

# 2. Select 18 widely distributed points (6 per class)
selected_indices = []
selected_labels = []

# Class names & colors
colors = ['#7f8c8d', '#2980b9', '#d35400'] # Gray, Blue, Orange
class_names = ["Background", "Aqueous Liquid", "Organic Liquid"]

print("\nSelecting 18 representative points...")
for class_id in range(3):
    idx_in_class = np.where(std_labels_0 == class_id)[0]
    
    # Pick 6 points evenly spaced along the indices
    pick_indices = idx_in_class[np.linspace(0, len(idx_in_class) - 1, 6, dtype=int)]
    selected_indices.extend(pick_indices)
    selected_labels.extend([class_id] * 6)

selected_indices = np.array(selected_indices)
selected_labels = np.array(selected_labels)

# Extract Frame 0's reference spectra for these 18 points
ref_spectra = spectral_0[selected_indices] # Shape: (18, 96)
selected_coords = coords_0[selected_indices]  # Shape: (18, 2)

for i in range(18):
    print(f"Point {i+1:2d} | Label: {class_names[selected_labels[i]]:15s} | XY: ({selected_coords[i, 0]:.1f}, {selected_coords[i, 1]:.1f})")

# 3. Process every 10th frame and build slow animation
print("\nGenerating dashboard animation (every 10th frame)...")
gif_frames = []

# Create a wide two-panel layout figure
fig = plt.figure(figsize=(16, 9), dpi=90)

for f_idx in range(0, num_frames, 10):
    frame = reader.get_frame(f_idx)
    scene_image = frame['scene_image']
    spectral_data = frame['spectral_data']
    coords = frame['coordinates']
    
    # Predict consistently
    pred_raw = kmeans.predict(spectral_data)
    pred_std = np.array([id_mapping[lbl] for lbl in pred_raw])
    
    # Clear figure
    fig.clf()
    
    # Left Column: Spatial Segmentation Scatter Overlay (takes up about 45% width)
    ax_map = fig.add_axes([0.05, 0.08, 0.40, 0.84])
    ax_map.imshow(scene_image, cmap='gray', extent=[0, 2048, 2432, 0])
    
    for class_id in range(3):
        idx = np.where(pred_std == class_id)[0]
        ax_map.scatter(coords[idx, 0], coords[idx, 1], c=colors[class_id], s=1.0, alpha=0.80, edgecolors='none')
    
    # Overlay the 18 numbered points
    for i in range(18):
        pt_lbl = i + 1
        x, y = coords[selected_indices[i]]
        # Plot circle
        ax_map.scatter(x, y, facecolors=colors[selected_labels[i]], edgecolors='black', s=60, linewidths=1.2, zorder=5)
        # Add text label
        ax_map.text(x + 35, y - 35, str(pt_lbl), fontsize=8, color='black', ha='center', va='center',
                    bbox=dict(boxstyle="circle,pad=0.2", fc="white", ec="black", lw=0.8, alpha=0.9), zorder=6)
        
    ax_map.set_title(f'Spectral Segmentation Map | Frame {f_idx:03d}', fontsize=12, fontweight='bold', pad=10)
    ax_map.set_xlim(0, 2048)
    ax_map.set_ylim(2432, 0)
    ax_map.axis('off')
    
    # Right Column: 6x3 Grid of Wavelength Curves (takes up about 50% width)
    # 6 rows, 3 columns
    for i in range(18):
        row = i // 3
        col = i % 3
        
        # Calculate axis position
        # left = 0.50 + col * 0.16
        # bottom = 0.88 - row * 0.15
        left = 0.49 + col * 0.165
        bottom = 0.84 - row * 0.145
        width = 0.15
        height = 0.11
        
        ax_spec = fig.add_axes([left, bottom, width, height])
        
        # Plot Frame 0 reference curve (dashed gray line)
        ax_spec.plot(wavelengths, ref_spectra[i], color='#95a5a6', linestyle='--', linewidth=1.0, alpha=0.7, label='Frame 0')
        
        # Plot Current Frame spectrum (solid line colored by current classification)
        current_spec = spectral_data[selected_indices[i]]
        current_cls = pred_std[selected_indices[i]]
        ax_spec.plot(wavelengths, current_spec, color=colors[current_cls], linewidth=1.5, label='Current')
        
        # Set titles and styles
        ax_spec.set_title(f'Point {i+1} ({class_names[selected_labels[i]][:7]})', fontsize=8, pad=2, fontweight='bold')
        ax_spec.set_xlim(440, 900)
        ax_spec.set_ylim(-0.002, 0.05)
        ax_spec.grid(True, linestyle=':', alpha=0.3)
        ax_spec.tick_params(axis='both', which='both', labelsize=6)
        
        if row == 5:
            ax_spec.set_xlabel('nm', fontsize=7, labelpad=1)
        if col == 0:
            ax_spec.set_ylabel('Reflectance', fontsize=7, labelpad=1)
            
    # Save the composite figure
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05)
    buf.seek(0)
    img = Image.open(buf)
    img.load()
    gif_frames.append(img)
    buf.close()
    
    if (f_idx + 10) % 50 == 0 or f_idx == num_frames - 1:
        print(f"Compiled diagnostic frame {f_idx + 1}/{num_frames}")

plt.close(fig)

# Save slow speed animation
if gif_frames:
    gif_filename = os.path.join(output_dir, "liquid_segmentation_diagnostic_slow.gif")
    print(f"\nCompiling slow animated GIF: {gif_filename}...")
    gif_frames[0].save(
        gif_filename,
        save_all=True,
        append_images=gif_frames[1:],
        duration=200, # 2x slower (200ms per frame)
        loop=0
    )
    print("Dashboard diagnostic slow GIF compiled successfully!")
else:
    print("Error: No frames generated.")
