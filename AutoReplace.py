import os
import random
import time
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageOps
import ctypes

# ---------------- Supported formats ----------------
valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.gif')

# ---------------- Ask for folders ----------------
from tkinter import filedialog
import tkinter as tk
root = tk.Tk()
root.withdraw()

target_folder = filedialog.askdirectory(title="Select Target Folder (images to be replaced)")
if not target_folder:
    ctypes.windll.user32.MessageBoxW(0, "No target folder selected!", "Error", 0x10)
    exit(1)

source_folder = filedialog.askdirectory(title="Select Source Folder (images to replace with)")
if not source_folder:
    ctypes.windll.user32.MessageBoxW(0, "No source folder selected!", "Error", 0x10)
    exit(1)

# ---------------- Options ----------------
flip_choice = ctypes.windll.user32.MessageBoxW(
    0, "Do you want the images to be flipped vertically?", "Option", 0x24
)
flip_images = (flip_choice == 6)

skip_transparency_choice = ctypes.windll.user32.MessageBoxW(
    0, "Skip replacing images with transparency?", "Option", 0x24
)
skip_transparency = (skip_transparency_choice == 6)

preserve_transparency_choice = ctypes.windll.user32.MessageBoxW(
    0, "Preserve transparent pixels when replacing?", "Option", 0x24
)
preserve_transparency = (preserve_transparency_choice == 6)

fast_mode_choice = ctypes.windll.user32.MessageBoxW(
    0, "Enable Ultra-Fast Mode? (lower quality, faster)", "Option", 0x24
)
resample = Image.BILINEAR if fast_mode_choice == 6 else Image.BICUBIC

# ---------------- Collect source images ----------------
source_images = []
for r, _, files in os.walk(source_folder):
    for f in files:
        if f.lower().endswith(valid_exts):
            source_images.append(os.path.join(r, f))
if not source_images:
    ctypes.windll.user32.MessageBoxW(0, "No valid images found in source folder!", "Error", 0x10)
    exit(1)

random.shuffle(source_images)
source_cycle = cycle(source_images)

# ---------------- Collect target images ----------------
target_images = []
for r, _, files in os.walk(target_folder):
    for f in files:
        if f.lower().endswith(valid_exts):
            target_images.append(os.path.join(r, f))
if not target_images:
    ctypes.windll.user32.MessageBoxW(0, "No valid images found in target folder!", "Error", 0x10)
    exit(1)

total_targets = len(target_images)

# ---------------- Worker function ----------------
def process_image(i, target_path, source_path):
    try:
        target_img = Image.open(target_path)
        source_img = Image.open(source_path)

        # Transparency skip (only if NOT preserving)
        if skip_transparency and not preserve_transparency:
            if target_img.mode in ("RGBA", "LA") or ("transparency" in target_img.info):
                print(f"[{i}/{total_targets}] Skipped {target_path} (transparent)")
                return "skipped"

        if target_img.mode != "RGBA":
            target_img = target_img.convert("RGBA")
        if source_img.mode != "RGBA":
            source_img = source_img.convert("RGBA")

        if flip_images:
            source_img = ImageOps.flip(source_img)

        source_resized = source_img.resize(target_img.size, resample)

        if preserve_transparency and target_img.mode == "RGBA":
            # Use target alpha channel
            target_alpha = target_img.getchannel("A")
            source_resized.putalpha(target_alpha)

        source_resized.save(target_path)

        print(f"[{i}/{total_targets}] Replaced {target_path} with {os.path.basename(source_path)}"
              + (" (flipped)" if flip_images else ""))

        return "replaced"
    except Exception as e:
        print(f"[{i}/{total_targets}] ERROR with {target_path}: {e}")
        return "error"

# ---------------- Main processing ----------------
start_time = time.time()

replaced_count = skipped_count = error_count = 0

with ThreadPoolExecutor() as executor:
    futures = {
        executor.submit(process_image, i, target, next(source_cycle)): target
        for i, target in enumerate(target_images, start=1)
    }

    for future in as_completed(futures):
        result = future.result()
        if result == "replaced":
            replaced_count += 1
        elif result == "skipped":
            skipped_count += 1
        elif result == "error":
            error_count += 1

elapsed = round(time.time() - start_time, 2)

# ---------------- Summary ----------------
summary_message = (
    f"✅ Done Replacing!\n\n"
    f"Total images processed: {total_targets}\n"
    f"Replaced: {replaced_count}\n"
    f"Skipped (transparent): {skipped_count}\n"
    f"Errors: {error_count}\n\n"
    f"Resize Mode: {'Ultra-Fast (BILINEAR)' if resample == Image.BILINEAR else 'Standard (BICUBIC)'}\n"
    f"Flip Images: {'Yes' if flip_images else 'No'}\n"
    f"Preserve Transparency: {'Yes' if preserve_transparency else 'No'}\n"
    f"Skip Transparent Images: {'Yes' if skip_transparency else 'No'}\n"
    f"CPU Workers: {os.cpu_count()}\n"
    f"Elapsed Time: {elapsed} seconds"
)

ctypes.windll.user32.MessageBoxW(0, summary_message, "Repaint Script - Summary", 0x40)
