---
name: image-processing
description: Guidelines and best practices for treating digital scientific images as data, ensuring integrity through proper manipulation, documentation, and testing.
---

# Image Processing

## Overview

Image processing involves the manipulation and analysis of digital images. In scientific contexts, images are data — not mere illustrations. Best practices emphasize preserving raw data, avoiding degrading filters, performing simple global adjustments, and rigorously documenting and testing the processing pipeline. The goal is to produce reproducible, trustworthy results.

## When to Use

- When analyzing quantitative data from images (e.g., intensity measurements, morphometry).
- When preparing figures for publication, where integrity of the original data must be maintained.
- When developing or applying image processing algorithms (e.g., segmentation, enhancement) in research or production.
- When comparing images acquired under different conditions (should be acquired identically).
- When documenting and testing image processing code for reliability and reproducibility.

## Process

1. **Retain the Original**  
   Always work on a copy of the raw image file. The original must be preserved unchanged.

2. **Treat Images as Data**  
   Do not alter pixel values arbitrarily. Every manipulation should be justified and recorded.

3. **Avoid Degrading Filters**  
   Do not use software filters (e.g., smoothing, sharpening) that modify data without scientific justification.

4. **Make Only Simple Global Adjustments**  
   Adjust brightness, contrast, or color balance across the entire image. Localized manipulations are questionable unless applied uniformly.

5. **Perform Intensity Measurements on Raw Data**  
   Calibrate measurements to a known standard. Never measure from manipulated images.

6. **Use Lossless Compression**  
   Avoid lossy compression (e.g., JPEG) that discards data. Prefer TIFF, PNG, or proprietary raw formats.

7. **Document Code and Data**  
   Use version control (Git) and reproducible environments (Docker, Conda). Comment your processing steps.

8. **Apply Unit Testing and Code Quality Tools**  
   Test individual functions (e.g., using pytest) to ensure correct behavior.

9. **Use Image Data Visualization and Interpretation Tools**  
   Employ viewers (e.g., ImageJ, napari, matplotlib) to inspect before and after processing.

10. **Follow Standards and Guidelines**  
    Adhere to community standards (e.g., QUAREP-LiMi, MIAPEG) for image processing and reporting.

## Verification

- Confirm that the original raw image file is stored and unchanged (check checksums if needed).
- Verify that all adjustments are global (check pixel value changes in multiple regions; they should be identical).
- Check that no cloning, retouching, or region-specific editing was performed (use difference masks or histogram comparisons).
- For publications, include the processing workflow as a figure or note in methods.
- Validate that unit tests pass for all image processing functions.
- Re-run the entire pipeline in a clean environment to ensure reproducibility.