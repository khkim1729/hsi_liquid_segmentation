import os
import struct
import numpy as np

class LivingOpticsReader:
    """
    A lightweight, high-performance Python parser for Living Optics proprietary `.lo` (LOFMT) files.
    Decodes the raw binary structure containing concatenated spatial-spectral frames, 
    extracting high-resolution scene images, sparse spectral samples, and physical metadata.
    """
    
    MAGIC = b'\x93LOPROCESSEDFMT\x00'
    FRAME_SIZE = 6699822
    METADATA_SIZE = 35597
    DATA_OFFSET = 35630
    IMAGE_SIZE = 2048 * 2432 * 1
    SPECTRAL_SIZE = 4384 * 96 * 4
    
    def __init__(self, filepath):
        self.filepath = filepath
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
            
        self.file_size = os.path.getsize(filepath)
        if self.file_size % self.FRAME_SIZE != 0:
            print(f"Warning: File size ({self.file_size} bytes) is not a perfect multiple of "
                  f"frame size ({self.FRAME_SIZE} bytes). Possibility of truncation.")
                  
        self.num_frames = self.file_size // self.FRAME_SIZE
        print(f"Initialized LivingOpticsReader | Total Frames: {self.num_frames} | File size: {self.file_size / (1024**3):.2f} GB")
        
        # Load header metadata from the first frame
        self._load_metadata()

    def _load_metadata(self):
        """Parses physical sensor configurations, wavelengths, and coordinates from the first frame's header."""
        with open(self.filepath, 'rb') as f:
            # Verify magic signature
            magic = f.read(16)
            if magic != self.MAGIC:
                raise ValueError("Invalid file format: Magic signature mismatch. Expected LOPROCESSEDFMT.")
                
            # Read metadata block
            f.seek(33)
            meta_block = f.read(self.METADATA_SIZE)
            
        # Parse scalar metadata at specific odd offsets
        # Values decoded using Little Endian 32-bit representations
        self.num_samples = struct.unpack_from("<I", meta_block, 0)[0]        # Offset 33 (relative 0)
        self.num_bands = struct.unpack_from("<I", meta_block, 4)[0]          # Offset 37 (relative 4)
        self.width = struct.unpack_from("<I", meta_block, 8)[0]              # Offset 41 (relative 8)
        self.height = struct.unpack_from("<I", meta_block, 12)[0]            # Offset 45 (relative 12)
        
        # Exposure / Integration time in nanoseconds
        self.exposure_ns = struct.unpack_from("<I", meta_block, 28)[0]       # Offset 61 (relative 28)
        self.exposure_ms = self.exposure_ns / 1_000_000.0
        
        # Frame rate in millihertz (mHz)
        self.fps_mhz = struct.unpack_from("<I", meta_block, 32)[0]           # Offset 65 (relative 32)
        self.fps = self.fps_mhz / 1000.0
        
        # Parse wavelengths (float32 array, starts at offset 174 -> relative offset 141)
        self.wavelengths = []
        for i in range(self.num_bands):
            w = struct.unpack_from("<f", meta_block, 141 + i * 4)[0]
            self.wavelengths.append(w)
        self.wavelengths = np.array(self.wavelengths, dtype=np.float32)
        
        # Parse sparse coordinates (float32 pairs (x, y), starts at offset 558 -> relative offset 525)
        coords = []
        for i in range(self.num_samples):
            x = struct.unpack_from("<f", meta_block, 525 + i * 8)[0]
            y = struct.unpack_from("<f", meta_block, 525 + i * 8 + 4)[0]
            coords.append((x, y))
        self.coordinates = np.array(coords, dtype=np.float32)

    def __len__(self):
        return self.num_frames

    def get_frame(self, frame_idx):
        """
        Retrieves the decoded data for a specific frame index.
        
        Parameters:
            frame_idx (int): The zero-based index of the frame (0 to num_frames - 1).
            
        Returns:
            dict: A dictionary containing:
                - 'scene_image': (2432, 2048) uint8 array of the scene camera.
                - 'spectral_data': (4384, 96) float32 array of spectral sample values.
                - 'coordinates': (4384, 2) float32 spatial coordinates of samples.
                - 'wavelengths': (96,) float32 wavelengths in nm.
                - 'exposure_ms': Exposure time in milliseconds.
                - 'fps': Frames per second.
        """
        if frame_idx < 0 or frame_idx >= self.num_frames:
            raise IndexError(f"Frame index {frame_idx} out of range (0 to {self.num_frames - 1}).")
            
        frame_start = frame_idx * self.FRAME_SIZE
        
        with open(self.filepath, 'rb') as f:
            # Seek directly to the data block of the requested frame
            f.seek(frame_start + self.DATA_OFFSET)
            raw_data = f.read(self.IMAGE_SIZE + self.SPECTRAL_SIZE)
            
        # Slice and reshape image and spectral data
        scene_bytes = raw_data[:self.IMAGE_SIZE]
        spectral_bytes = raw_data[self.IMAGE_SIZE:]
        
        scene_image = np.frombuffer(scene_bytes, dtype=np.uint8).reshape(self.height, self.width)
        spectral_data = np.frombuffer(spectral_bytes, dtype=np.float32).reshape(self.num_samples, self.num_bands)
        
        return {
            'scene_image': scene_image,
            'spectral_data': spectral_data,
            'coordinates': self.coordinates,
            'wavelengths': self.wavelengths,
            'exposure_ms': self.exposure_ms,
            'fps': self.fps
        }

    def print_summary(self):
        """Prints a comprehensive and beautiful summary of the dataset characteristics."""
        print("=" * 60)
        print("           LIVING OPTICS HSI DATASET SUMMARY            ")
        print("=" * 60)
        print(f"File Path:          {self.filepath}")
        print(f"File Size:          {self.file_size / (1024**3):.4f} GB ({self.file_size:,} bytes)")
        print(f"Total Frames:       {self.num_frames}")
        print(f"Frame Size:         {self.FRAME_SIZE:,} bytes")
        print("-" * 60)
        print(f"Scene Resolution:   {self.width} x {self.height} (Pixel count: {self.width*self.height:,})")
        print(f"Spectral Samples:   {self.num_samples} sparse samples per frame")
        print(f"Spectral Bands:     {self.num_bands} bands ({self.wavelengths[0]:.2f} nm to {self.wavelengths[-1]:.2f} nm)")
        print(f"Frame Rate (FPS):   {self.fps:.2f} Hz")
        print(f"Exposure Time:      {self.exposure_ms:.2f} ms")
        print("=" * 60)

# Quick demonstration of self-validation if run directly
if __name__ == "__main__":
    filepath = "/data/hsi_fm_bench_123/more_projects/all_spectrum_detection_proj/liquid_segmentation/data/spectral-detection/liquid-segmentation.lo"
    reader = LivingOpticsReader(filepath)
    reader.print_summary()
    
    # Load Frame 0
    print("\nLoading Frame 0...")
    frame = reader.get_frame(0)
    print("Frame 0 loaded successfully!")
    print("Image stats:", frame['scene_image'].shape, "Mean:", frame['scene_image'].mean())
    print("Spectral stats:", frame['spectral_data'].shape, "Mean:", frame['spectral_data'].mean())
