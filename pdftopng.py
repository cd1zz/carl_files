import os
import subprocess
import json
from pdf2image import convert_from_path

def find_pdfs(directory):
    """Recursively find all PDF files in the directory and subdirectories."""
    pdf_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    return sorted(pdf_files)  # Sort files for consistent processing order

def load_checkpoint():
    """Load the last processed files and pages from the checkpoint file."""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            checkpoint = json.load(f)
        print(f"Loaded checkpoint: {checkpoint}")
        return checkpoint
    return {}

def save_checkpoint(checkpoint):
    """Save the current files and their last processed pages to the checkpoint file."""
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint, f)
    print(f"Checkpoint saved: {checkpoint}")

def get_existing_images(output_directory):
    """Get a list of existing image files in the output directory."""
    existing_images = set()
    for root, dirs, files in os.walk(output_directory):
        for file in files:
            if file.endswith('.png'):
                existing_images.add(file)
    return existing_images

def save_images_from_pdf(pdf_path, output_directory, checkpoint, start_page=0, existing_images=None):
    """Convert each page of the PDF to a PNG image and save to disk, one page at a time to optimize memory usage."""
    if existing_images is None:
        existing_images = set()

    # Determine the subfolder name based on the PDF's parent folder
    subfolder_name = os.path.basename(os.path.dirname(pdf_path))
    subfolder_path = os.path.join(output_directory, subfolder_name)

    # Create the output directory if it doesn't exist
    if not os.path.exists(subfolder_path):
        os.makedirs(subfolder_path)

    print(f"Processing: {pdf_path}")
    try:
        # Get the total number of pages using pdfinfo (comes with poppler-utils)
        result = subprocess.run(["pdfinfo", pdf_path], stdout=subprocess.PIPE, text=True)
        for line in result.stdout.splitlines():
            if "Pages:" in line:
                total_pages = int(line.split(":")[1].strip())
                break
        
        print(f"Total pages in {pdf_path}: {total_pages}")

        for page_number in range(start_page, total_pages):
            image_filename = f"{os.path.basename(pdf_path)[:-4]}_page_{page_number+1}.png"
            image_path = os.path.join(subfolder_path, image_filename)

            if image_filename in existing_images:
                print(f"Skipping {image_filename} (already exists)")
                continue

            images = convert_from_path(pdf_path, first_page=page_number+1, last_page=page_number+1)
            images[0].save(image_path, 'PNG')
            print(f"Saved {image_path}")

            # Save checkpoint after processing each page
            checkpoint[pdf_path] = page_number + 1
            save_checkpoint(checkpoint)

            # Clean up to free memory
            del images

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")

def process_pdfs(directory, output_directory):
    """Process all PDFs in the given directory, convert them to images, and save to disk."""
    pdf_files = find_pdfs(directory)

    checkpoint = load_checkpoint()

    print(f"Found {len(pdf_files)} PDF files in directory '{directory}'")

    # Get the existing images in the output directory
    existing_images = get_existing_images(output_directory)

    for pdf_file in pdf_files:
        last_page = checkpoint.get(pdf_file, 0)
        save_images_from_pdf(pdf_file, output_directory, checkpoint, start_page=last_page, existing_images=existing_images)

# Directory containing PDFs
pdf_directory = "./pdfs/"
output_directory = "./output_images/"
checkpoint_file = "checkpoint_pdftopng.json"

process_pdfs(pdf_directory, output_directory)
