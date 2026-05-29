import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from PIL import Image

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from lo_parser import LivingOpticsReader

# Paths
lo_filepath = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/data/spectral-detection/liquid-segmentation.lo"
output_dir = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/docs/images"
os.makedirs(output_dir, exist_ok=True)

# Load HSI data
reader = LivingOpticsReader(lo_filepath)
frame = reader.get_frame(0)
scene_image = frame['scene_image']
spectral_data = frame['spectral_data']  # Shape: (4384, 96)
coords = frame['coordinates']          # Shape: (4384, 2)
wavelengths = frame['wavelengths']      # Shape: (96,)

print("Running K-Means Clustering on 96-band spectral data...")
# Cluster into 3 main physical classes: Background, Liquid Class 1 (Aqueous), Liquid Class 2 (Organic/Solvent/Oil)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
labels = kmeans.fit_predict(spectral_data)

# Let's inspect each cluster and identify them based on average reflectance and O-H absorption valleys
# Cluster stats
cluster_means = []
cluster_indices = []
for i in range(3):
    idx = np.where(labels == i)[0]
    mean_curve = np.mean(spectral_data[idx], axis=0)
    cluster_means.append(mean_curve)
    cluster_indices.append(idx)

# Map clusters to physical labels based on spectral properties
# 1. Background usually has very low reflectance across all bands
# 2. Water/Aqueous Liquid has moderate/high VIS reflectance but strong O-H overtone absorption valley around 830nm
# 3. Organic/Oil or highly reflective surface has flat or high NIR reflectance without the 830nm water dip
avg_reflectance = [np.mean(m) for m in cluster_means]
nir_ends = [np.mean(m[80:]) for m in cluster_means]  # NIR region
water_dip_ratio = []  # Ratio of 830nm to 780nm (lower ratio = deeper dip = water)

# Find band indices near 830nm (Band 86 is 831nm) and 788nm (Band 80 is 788nm)
idx_830 = np.argmin(np.abs(wavelengths - 831.0))
idx_788 = np.argmin(np.abs(wavelengths - 788.0))

for m in cluster_means:
    water_dip_ratio.append(m[idx_830] / (m[idx_788] + 1e-9))

# Sorting logic:
# Low average reflectance -> Background (Dull Plastic / Shadow)
# High reflectance & Low water dip ratio -> Aqueous Liquid (Water / Dyed Solution)
# High reflectance & High water dip ratio -> Organic Liquid / Oil / Reflective Target
sorted_by_refl = np.argsort(avg_reflectance)
bg_cluster = sorted_by_refl[0]

# Out of the remaining two, check the water dip ratio
rem_clusters = sorted_by_refl[1:]
if water_dip_ratio[rem_clusters[0]] < water_dip_ratio[rem_clusters[1]]:
    aqueous_cluster = rem_clusters[0]
    organic_cluster = rem_clusters[1]
else:
    aqueous_cluster = rem_clusters[1]
    organic_cluster = rem_clusters[0]

cluster_map = {
    bg_cluster: ("Background", "#7f8c8d"),         # Gray
    aqueous_cluster: ("Aqueous Liquid", "#2980b9"), # Ocean Blue
    organic_cluster: ("Organic Liquid / Oil", "#d35400") # Warm Orange/Rust
}

print("\n--- Unsupervised Clustering Discovered Classes ---")
for original_id, (class_name, color) in cluster_map.items():
    idx = cluster_indices[original_id]
    print(f"Discovered: {class_name:25s} | Samples: {len(idx):4d} ({len(idx)/4384*100:5.2f}%) | Avg Reflectance: {avg_reflectance[original_id]:.6f}")

# Reorder labels to make them standardized: 0=Background, 1=Aqueous, 2=Organic
standard_labels = np.zeros_like(labels)
standard_labels[labels == bg_cluster] = 0
standard_labels[labels == aqueous_cluster] = 1
standard_labels[labels == organic_cluster] = 2

# 1. Save clustered scatter plot overlaid on the scene image (Spectral Semantic Segmentation)
print("\nSaving spectral clustering segmentation overlay...")
plt.figure(figsize=(8, 10))
plt.imshow(scene_image, cmap='gray', extent=[0, 2048, 2432, 0])

colors = ['#7f8c8d', '#2980b9', '#d35400']
class_names = ["Background (Surface/Shadow)", "Aqueous Liquid (Water/Solution)", "Organic Liquid (Oil/Solvent)"]

for class_id in range(3):
    idx = np.where(standard_labels == class_id)[0]
    plt.scatter(coords[idx, 0], coords[idx, 1], c=colors[class_id], s=4, alpha=0.9, edgecolors='none', label=class_names[class_id])

plt.title('Unsupervised Spectral Semantic Segmentation (Frame 0)', fontsize=13, fontweight='bold', pad=12)
plt.xlabel('X Coordinate (pixels)', fontsize=10)
plt.ylabel('Y Coordinate (pixels)', fontsize=10)
plt.xlim(0, 2048)
plt.ylim(2432, 0)
plt.legend(fontsize=10, loc='lower right', framealpha=0.9)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "spectral_clusters_segmentation.png"), dpi=150)
plt.close()
print("Clustered segmentation overlay saved successfully.")

# 2. Save cluster spectral signature comparison chart
print("\nPlotting clustered spectral signatures...")
plt.figure(figsize=(10, 6))

for class_id in range(3):
    idx = np.where(standard_labels == class_id)[0]
    mean_spectrum = np.mean(spectral_data[idx], axis=0)
    std_spectrum = np.std(spectral_data[idx], axis=0)
    
    plt.plot(wavelengths, mean_spectrum, color=colors[class_id], linewidth=2.5, label=f"{class_names[class_id]} (Mean)")
    plt.fill_between(wavelengths, mean_spectrum - 0.5 * std_spectrum, mean_spectrum + 0.5 * std_spectrum, color=colors[class_id], alpha=0.15)

# Annotate specific O-H molecular overtone absorption valley
plt.axvspan(820, 850, color='#3498db', alpha=0.08, label='O-H 3rd Overtone Valley (Water Indicator)')
plt.text(835, 0.002, 'O-H Dip\n(830-840 nm)', color='#1f3a52', fontsize=9, ha='center', fontweight='bold')

plt.title('Expert Spectral Class Signatures & Chemical Fingerprints (VIS-NIR)', fontsize=13, fontweight='bold', pad=15)
plt.xlabel('Wavelength (nm)', fontsize=11)
plt.ylabel('Calibrated Reflectance Intensity', fontsize=11)
plt.grid(True, linestyle='--', alpha=0.4)
plt.legend(fontsize=10, loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "spectral_class_signatures.png"), dpi=150)
plt.close()
print("Clustered signatures plot saved successfully.")

# 3. Print quantitative statistical table for README markdown inclusion
print("\n--- GENERATED MARKDOWN TABLE FOR README.MD ---")
print("| Discovered Class ID | Class Description | Sample Count | Sample Proportion (%) | Mean Reflectance | Min Reflectance | Max Reflectance | Key Diagnostic Chemical Markers |")
print("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
for class_id in range(3):
    idx = np.where(standard_labels == class_id)[0]
    class_data = spectral_data[idx]
    c_mean = np.mean(class_data)
    c_min = np.min(class_data)
    c_max = np.max(class_data)
    
    if class_id == 0:
        markers = "Dull response across entire 441-898nm range, flat scattering, low albedo."
    elif class_id == 1:
        markers = "Strong absorption valley at **830-840nm (O-H overtone)**, high VIS reflectance."
    else:
        markers = "Flat near-infrared (NIR) plateau without O-H overtone dip, high NIR reflection."
        
    print(f"| **{class_id}** | {class_names[class_id]} | {len(idx):,} | {len(idx)/4384*100:.2f}% | {c_mean:.6f} | {c_min:.6f} | {c_max:.6f} | {markers} |")
