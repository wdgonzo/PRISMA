#!/usr/bin/env python3
"""
PRISMA Icon Generator
=====================
Creates a simple icon file for PRISMA application.

This creates a basic icon with the text "P" on a blue background.
For a professional icon, replace prisma_icon.ico with a custom design.

Usage:
    python create_icon.py

Output:
    prisma_icon.ico - Windows icon file

Requirements:
    PIL/Pillow: pip install Pillow
"""

import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow not installed")
    print("Install with: pip install Pillow")
    sys.exit(1)


def create_prisma_icon(output_path='prisma_icon.ico'):
    """
    Create PRISMA icon file.

    Args:
        output_path: Output filename
    """
    # Create images at multiple sizes for Windows icon
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for size in sizes:
        # Create image with blue background
        img = Image.new('RGB', size, color='#2196F3')  # Material Blue
        draw = ImageDraw.Draw(img)

        # Try to use a nice font, fallback to default
        try:
            # Adjust font size based on icon size
            font_size = int(size[0] * 0.6)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Use default font
            font = ImageFont.load_default()

        # Draw "P" for PRISMA
        text = "P"

        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center text
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2 - bbox[1]

        # Draw text in white
        draw.text((x, y), text, fill='white', font=font)

        # Add border
        border_width = max(1, size[0] // 32)
        draw.rectangle(
            [(0, 0), (size[0]-1, size[1]-1)],
            outline='#1976D2',  # Darker blue
            width=border_width
        )

        images.append(img)

    # Save as ICO file
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images]
    )

    print(f"✓ Created icon: {output_path}")
    print(f"  Sizes: {', '.join(f'{s[0]}x{s[1]}' for s in sizes)}")


def main():
    """Main entry point."""
    print("="*60)
    print("PRISMA Icon Generator")
    print("="*60)

    create_prisma_icon('prisma_icon.ico')

    print("\nIcon created successfully!")
    print("\nFor a professional icon, replace prisma_icon.ico with")
    print("a custom design from a graphic designer or icon tool.")
    print("="*60)


if __name__ == "__main__":
    main()
