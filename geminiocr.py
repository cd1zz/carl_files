import os
import sys
import google.generativeai as genai
import json
import csv
import traceback
import logging
from datetime import datetime
from google.protobuf.json_format import MessageToDict
from google.generativeai.types.generation_types import StopCandidateException

# Configuration for the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Configure the Gemini API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Set up logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

def log_unfinished_file_csv(csv_path, file_path, finish_reason):
    with open(csv_path, "a", newline='') as csvfile:
        log_writer = csv.writer(csvfile)
        log_writer.writerow([file_path, finish_reason])

def load_unfinished_files(csv_path):
    unfinished_files = set()
    if os.path.exists(csv_path):
        with open(csv_path, "r") as csvfile:
            log_reader = csv.reader(csvfile)
            for row in log_reader:
                if len(row) > 0:
                    unfinished_files.add(row[0])  # Assuming the file path is the first column
    return unfinished_files

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini and returns the file metadata."""
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        logging.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        logging.error(f"Failed to upload file {path}: {e}")
        return None

def delete_gemini_file(file_uri):
    """Deletes a file from Gemini AI using its URI."""
    try:
        file_id = file_uri.split('/')[-1]
        genai.delete_file(file_id)
        logging.info(f"Deleted file with URI: {file_uri}")
    except Exception as e:
        logging.error(f"Failed to delete file with URI {file_uri}: {e}")

def process_images(directory, output_directory, unfinished_files, csv_path):
    """Recursively process each .png file in the directory and subdirectories, send it to Gemini, and save the text output."""
    
    finish_reason_dict = {
        0: "Unspecified reason",
        1: "Natural stop (STOP)",
        2: "Max tokens reached (MAX_TOKENS)",
        3: "Safety concern (SAFETY)",
        4: "Recitation detected (RECITATION)",
        5: "Unknown reason (OTHER)"
    }

    total_files = 0  
    processed_files = 0  
    
    for root, _, files in os.walk(directory):
        text_root = os.path.join(output_directory, os.path.relpath(root, directory))
        os.makedirs(text_root, exist_ok=True)

        image_files = sorted([f for f in files if f.endswith('.png')])
        total_files += len(image_files)
        logging.info(f"Processing {len(image_files)} files in directory: {root}")

        for image_file in image_files:
            output_file = os.path.join(text_root, f"{image_file[:-4]}.txt")
            
            if os.path.exists(output_file):
                continue

            image_path = os.path.join(root, image_file)

            if image_path in unfinished_files:
                continue

            logging.info(f"Processing: {image_path}")

            uploaded_file = upload_to_gemini(image_path, mime_type="image/png")
            if uploaded_file is None:
                continue

            extracted_text = ""
            response = None  
            error_handled = False  

            try:
                logging.info(f"Sending content for {image_path}")

                response = model.generate_content(
                    [uploaded_file, "\n\n", "Please convert the content of this image to plain text. Do not include unnecessary line breaks or newlines."]
                )

                logging.info(f"Response received for {image_path}")

                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    finish_reason = candidate.finish_reason
                    reason_text = finish_reason_dict.get(finish_reason, f"Unknown finish reason ({finish_reason})")

                    logging.info(f"Finish reason for {image_path}: {reason_text}")

                    if finish_reason == 2:  # Max tokens reached
                        logging.info(f"Max tokens reached for {image_path}, consider handling continuation.")
                        logging.info(f"Token data {response.usage_metadata}")

                    if finish_reason != 1:  # Not successful
                        log_unfinished_file_csv(csv_path, image_path, reason_text)

                    if finish_reason == 1:  # Successful
                        extracted_text += candidate.content.parts[0].text
                else:
                    logging.warning(f"Failed to extract text for {image_path}. No valid candidates returned.")
                    log_unfinished_file_csv(csv_path, image_path, "No valid candidates returned")
                    error_handled = True

            except StopCandidateException as sce:
                candidate = sce.args[0]  
                finish_reason = candidate.finish_reason
                reason_text = finish_reason_dict.get(finish_reason, f"Unknown finish reason ({finish_reason})")

                logging.info(f"Handled StopCandidateException for {image_path}: {sce}")
                log_unfinished_file_csv(csv_path, image_path, reason_text)
                error_handled = True

            except Exception as e:
                logging.error(f"An error occurred while processing {image_path}: {e}")
                logging.error(traceback.format_exc())  
                log_unfinished_file_csv(csv_path, image_path, f"Unexpected error: {e}")
                error_handled = True  

                if "429" in str(e):
                    logging.error(f"Rate limit error for {image_path}. Exiting.")
                    sys.exit()

            if not error_handled and extracted_text:
                with open(output_file, "w") as f:
                    f.write(extracted_text)
                logging.info(f"Saved text output to {output_file}")
                logging.info(extracted_text)
                processed_files += 1
            else:
                logging.warning(f"No text extracted for {image_path}")

            delete_gemini_file(uploaded_file.uri)

    logging.info(f"Total files: {total_files}")
    logging.info(f"Processed files: {processed_files}")

def main():
    image_directory = "./output_images/"
    output_directory = "./output_text/"
    csv_path = "./unfinished_files.csv"

    unfinished_files = load_unfinished_files(csv_path)

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    process_images(image_directory, output_directory, unfinished_files, csv_path)

if __name__ == "__main__":
    main()
