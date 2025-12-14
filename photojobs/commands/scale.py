"""Scale command - Resize images proportionally by longest side.

Usage:
    python3 -m photojobs scale --root /path/to/images --size 2000

Behavior:
- Processes all image files in the source folder
- Scales images proportionally so the longest side equals the specified size
- Preserves aspect ratio
- Outputs to parent folder with naming pattern: <folder>_<size>
- Example: BannerJPG → BannerJPG_2000 (if size=2000)
- Supported formats: .jpg, .jpeg, .png
"""

import sys
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow library is required for the scale command.")
    print("Install it with: pip3 install Pillow")
    sys.exit(1)

__all__ = ["run"]


def get_image_files(directory: Path) -> List[Path]:
    """Find all image files in the directory.

    Args:
        directory: Directory to search for images

    Returns:
        List of image file paths
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    image_files = []

    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix in image_extensions:
            image_files.append(file_path)

    return sorted(image_files)


def calculate_scaled_dimensions(original_width: int, original_height: int, target_long_side: int) -> Tuple[int, int]:
    """Calculate new dimensions maintaining aspect ratio.

    Args:
        original_width: Original image width
        original_height: Original image height
        target_long_side: Desired size for the longest side

    Returns:
        Tuple of (new_width, new_height)
    """
    # Determine which side is longer
    if original_width >= original_height:
        # Width is the long side
        scale_factor = target_long_side / original_width
        new_width = target_long_side
        new_height = int(original_height * scale_factor)
    else:
        # Height is the long side
        scale_factor = target_long_side / original_height
        new_height = target_long_side
        new_width = int(original_width * scale_factor)

    return new_width, new_height


def scale_image(source_path: Path, output_path: Path, target_long_side: int, quality: int = 95) -> bool:
    """Scale a single image.

    Args:
        source_path: Path to source image
        output_path: Path for output image
        target_long_side: Target size for longest side in pixels
        quality: JPEG quality (1-100), default 95

    Returns:
        True if successful, False otherwise
    """
    try:
        with Image.open(source_path) as img:
            # Get original dimensions
            original_width, original_height = img.size

            # Calculate new dimensions
            new_width, new_height = calculate_scaled_dimensions(
                original_width, original_height, target_long_side
            )

            # Check if scaling is needed
            if new_width == original_width and new_height == original_height:
                print(f"  Skipping {source_path.name} (already {target_long_side}px on long side)")
                return True

            # Scale the image using high-quality resampling
            scaled_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save the scaled image
            if source_path.suffix.lower() in {'.jpg', '.jpeg'}:
                scaled_img.save(output_path, 'JPEG', quality=quality, optimize=True)
            else:
                scaled_img.save(output_path)

            return True

    except Exception as e:
        print(f"  ERROR: Failed to scale {source_path.name}: {e}")
        return False


def run(args) -> int:
    """PhotoJobs CLI entrypoint for the scale command."""
    source_folder = Path(args.root).expanduser().resolve()
    target_size = args.size

    if not source_folder.exists():
        print(f"ERROR: Source folder not found: {source_folder}")
        return 1

    if not source_folder.is_dir():
        print(f"ERROR: Path is not a directory: {source_folder}")
        return 1

    if target_size <= 0:
        print(f"ERROR: Size must be a positive integer, got: {target_size}")
        return 1

    # Create output folder name: <source_folder_name>_<size>
    output_folder_name = f"{source_folder.name}_{target_size}"
    output_folder = source_folder.parent / output_folder_name

    print(f"Source folder: {source_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Target size:   {target_size}px (long side)")
    print()

    # Create output directory
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"Created output directory: {output_folder}")
    print()

    # Find all image files
    image_files = get_image_files(source_folder)

    if not image_files:
        print("WARNING: No image files found in source folder")
        print("Supported formats: .jpg, .jpeg, .png")
        return 0

    print(f"Found {len(image_files)} image(s) to process")
    print()

    # Process each image
    successful = 0
    skipped = 0
    failed = 0

    for idx, source_path in enumerate(image_files, start=1):
        output_path = output_folder / source_path.name

        print(f"[{idx}/{len(image_files)}] Processing: {source_path.name}")

        # Check if output file already exists
        if output_path.exists():
            print(f"  Skipping (output already exists): {output_path.name}")
            skipped += 1
            continue

        # Scale the image
        if scale_image(source_path, output_path, target_size):
            # Get dimensions for confirmation
            with Image.open(output_path) as img:
                width, height = img.size
                print(f"  Scaled to: {width}x{height}px → {output_path.name}")
            successful += 1
        else:
            failed += 1

    # Summary
    print()
    print("=== Summary ===")
    print(f"Total images:        {len(image_files)}")
    print(f"Successfully scaled: {successful}")
    print(f"Skipped:             {skipped}")
    print(f"Failed:              {failed}")
    print()
    print(f"Output folder: {output_folder}")

    return 0 if failed == 0 else 1
