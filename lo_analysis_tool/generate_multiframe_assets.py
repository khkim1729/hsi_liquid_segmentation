import os
import cv2
import numpy as np
from PIL import Image
import sys

# Add current tool folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from lo_parser import LivingOpticsReader

# Setup directories
lo_filepath = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/data/spectral-detection/liquid-segmentation.lo"
output_dir = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/docs/images"
os.makedirs(output_dir, exist_ok=True)

# Load HSI reader
reader = LivingOpticsReader(lo_filepath)
num_frames = len(reader)
print(f"Loaded LO dataset with {num_frames} frames.")

# 1. Extract multiple representative frames (0, 50, 100, 150, 200, 250, 300, 350)
extract_frames = [0, 50, 100, 150, 200, 250, 300, 350]
print("\nExtracting representative frames...")
for f_idx in extract_frames:
    if f_idx < num_frames:
        frame = reader.get_frame(f_idx)
        img_array = frame['scene_image']
        
        # Save as grayscale PNG
        img = Image.fromarray(img_array)
        img_resized = img.resize((512, 608), Image.Resampling.LANCZOS)
        img_filename = f"frame_{f_idx:03d}_scene.png"
        img_resized.save(os.path.join(output_dir, img_filename))
        print(f"Saved: {img_filename}")

# 2. Compile an MP4 video of the context scene
print("\nCompiling context scene video (MP4)...")
video_filename = os.path.join(output_dir, "liquid_segmentation_video.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Default mp4 codec
# We downscale to 512x608 for the video as well to keep file size reasonable
video_width, video_height = 512, 608
out = cv2.VideoWriter(video_filename, fourcc, 30.0, (video_width, video_height), isColor=False)

for f_idx in range(num_frames):
    frame = reader.get_frame(f_idx)
    img_array = frame['scene_image']
    
    # Resize frame for video
    img_resized = cv2.resize(img_array, (video_width, video_height), interpolation=cv2.INTER_AREA)
    out.write(img_resized)
    
    if (f_idx + 1) % 50 == 0 or f_idx == num_frames - 1:
        print(f"Written frame {f_idx + 1}/{num_frames} to video.")

out.release()
print(f"MP4 Video saved successfully: {video_filename}")

# 3. Compile a 5x speeded-up GIF (every 5th frame)
print("\nCompiling 5x speeded-up GIF...")
gif_filename = os.path.join(output_dir, "liquid_segmentation_fast.gif")
gif_frames = []

for f_idx in range(0, num_frames, 5):
    frame = reader.get_frame(f_idx)
    img_array = frame['scene_image']
    
    # Resize to 512x608 using PIL
    img = Image.fromarray(img_array)
    img_resized = img.resize((512, 608), Image.Resampling.LANCZOS)
    gif_frames.append(img_resized)

if gif_frames:
    # Save animated GIF (duration=100ms per frame, loop indefinitely)
    gif_frames[0].save(
        gif_filename,
        save_all=True,
        append_images=gif_frames[1:],
        duration=100,
        loop=0
    )
    print(f"Animated speed-up GIF saved successfully: {gif_filename}")
