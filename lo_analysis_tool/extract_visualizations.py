import os
import struct
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# Setup paths
lo_filepath = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/data/spectral-detection/liquid-segmentation.lo"
output_dir = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/docs/images"
os.makedirs(output_dir, exist_ok=True)

print("Reading first frame from .lo file...")
# Single frame size parameters
frame_size = 6699822
metadata_size = 35597
data_offset = 35630
image_size = 2048 * 2432 * 1
spectral_size = 4384 * 96 * 4

# Read the first frame
with open(lo_filepath, 'rb') as f:
    # 1. Read metadata block
    f.seek(33)
    metadata_bytes = f.read(metadata_size)
    # 2. Read data block
    f.seek(data_offset)
    data_bytes = f.read(image_size + spectral_size)

# Parse wavelengths (offset 174 in the frame, which is 174-33 = 141 in metadata_bytes)
wavelengths = []
for i in range(96):
    offset = 141 + i * 4
    w = struct.unpack_from("<f", metadata_bytes, offset)[0]
    wavelengths.append(w)

# Parse coordinates (offset 558 in the frame, which is 558-33 = 525 in metadata_bytes)
coords = []
for i in range(4384):
    offset = 525 + i * 8
    x = struct.unpack_from("<f", metadata_bytes, offset)[0]
    y = struct.unpack_from("<f", metadata_bytes, offset + 4)[0]
    coords.append((x, y))

# Parse image and spectra
scene_image = np.frombuffer(data_bytes[:image_size], dtype=np.uint8).reshape(2432, 2048)
spectral_data = np.frombuffer(data_bytes[image_size:], dtype=np.float32).reshape(4384, 96)

print("Extracted successfully!")
print("Wavelength range:", min(wavelengths), "-", max(wavelengths))
print("Scene image shape:", scene_image.shape)
print("Spectral data shape:", spectral_data.shape)

# 1. Save Scene Image (Downscaled by 4x for web viewing)
print("\nSaving scene image...")
img = Image.fromarray(scene_image)
img_resized = img.resize((512, 608), Image.Resampling.LANCZOS)
img_resized.save(os.path.join(output_dir, "frame_0_scene.png"))
print("Scene image saved.")

# 2. Save Spectral Curve Plot
print("\nPlotting spectral curves...")
# Let's find samples with high, medium, and low average reflectance
mean_spectra = np.mean(spectral_data, axis=1)
high_idx = np.argmax(mean_spectra)
low_idx = np.argmin(mean_spectra)
# Find a median one
median_val = np.median(mean_spectra)
med_idx = np.argmin(np.abs(mean_spectra - median_val))

plt.figure(figsize=(10, 6))
plt.plot(wavelengths, spectral_data[high_idx], label=f'High Reflectance (Sample {high_idx}, Coords: ({coords[high_idx][0]:.1f}, {coords[high_idx][1]:.1f}))', color='#e74c3c', linewidth=2)
plt.plot(wavelengths, spectral_data[med_idx], label=f'Medium Reflectance (Sample {med_idx}, Coords: ({coords[med_idx][0]:.1f}, {coords[med_idx][1]:.1f}))', color='#3498db', linewidth=2)
plt.plot(wavelengths, spectral_data[low_idx], label=f'Low Reflectance (Sample {low_idx}, Coords: ({coords[low_idx][0]:.1f}, {coords[low_idx][1]:.1f}))', color='#2ecc71', linewidth=2)

plt.title('Spectral Signatures from liquid-segmentation.lo (Frame 0)', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('Wavelength (nm)', fontsize=12)
plt.ylabel('Reflectance Intensity', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend(fontsize=10, loc='upper right')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "spectral_curves.png"), dpi=150)
plt.close()
print("Spectral curves plot saved.")

# 3. Save Spectral Sampling Overlay
print("\nPlotting sampling grid overlay...")
plt.figure(figsize=(8, 10))
# Plot the downscaled scene image as background
plt.imshow(scene_image, cmap='gray', extent=[0, 2048, 2432, 0])
xs = [c[0] for c in coords]
ys = [c[1] for c in coords]
# Plot coordinates as sparse scatter points
plt.scatter(xs, ys, c=mean_spectra, cmap='jet', s=3, alpha=0.8, edgecolors='none', label='Spectral Samples')
plt.colorbar(label='Mean Spectral Reflectance')
plt.title('Sparse Spectral Sampling Grid Overlaid on Scene Image', fontsize=12, fontweight='bold', pad=10)
plt.xlabel('X Coordinate (pixels)')
plt.ylabel('Y Coordinate (pixels)')
plt.xlim(0, 2048)
plt.ylim(2432, 0) # Flip y-axis to match image coordinates
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "spectral_sampling_grid.png"), dpi=150)
plt.close()
print("Sampling grid overlay saved.")

print("\nAll visualizations created successfully in:", output_dir)
