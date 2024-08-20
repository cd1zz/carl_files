import os
import sys
import google.generativeai as genai
import json
import csv
import traceback
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
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        print(f"Failed to upload file {path}: {e}")
        return None

def process_images(directory, output_directory, unfinished_files, csv_path):
    """Recursively process each .png file in the directory and subdirectories, send it to Gemini, and save the text output."""
    
    # Dictionary mapping finish_reason codes to human-readable descriptions
    finish_reason_dict = {
        0: "Unspecified reason",
        1: "Natural stop (STOP)",
        2: "Max tokens reached (MAX_TOKENS)",
        3: "Safety concern (SAFETY)",
        4: "Recitation detected (RECITATION)",
        5: "Unknown reason (OTHER)"
    }

    total_files = 0  # To track the total number of files
    processed_files = 0  # To track how many files were processed
    
    for root, _, files in os.walk(directory):
        text_root = os.path.join(output_directory, os.path.relpath(root, directory))
        os.makedirs(text_root, exist_ok=True)

        image_files = sorted([f for f in files if f.endswith('.png')])
        total_files += len(image_files)
        print(f"Processing {len(image_files)} files in directory: {root}")

        for image_file in image_files:
            output_file = os.path.join(text_root, f"{image_file[:-4]}.txt")
            
            # Check if the corresponding text file already exists
            if os.path.exists(output_file):
                print(f"Skipping {image_file}, corresponding text file already exists.")
                continue

            # Check if the file is a problem/unfinished file and skip
            image_path = os.path.join(root, image_file)

            if image_path in unfinished_files:
                print(f"Skipping {image_path}, as it is listed in unfinished_files.csv.")
                continue

            print(f"\nProcessing: {image_path}")

            uploaded_file = upload_to_gemini(image_path, mime_type="image/png")
            if uploaded_file is None:
                print(f"Skipping {image_file} due to upload failure.")
                continue

            extracted_text = None
            response = None  # Initialize response to ensure it's available in the except block
            error_handled = False  # Flag to indicate if the error has been handled

            try:
                print(f"Starting chat session for {image_path}")
                chat_session = model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": [
                                uploaded_file,
                                "Please convert the content of this image to plain text."
                            ],
                        },
                    ]
                )

                response = chat_session.send_message("Please convert the content of this image to plain text.")
                print(f"Response received for {image_path}")

                # Accessing the extracted text from the response object
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    finish_reason = candidate.finish_reason
                    reason_text = finish_reason_dict.get(finish_reason, f"Unknown finish reason ({finish_reason})")

                    print(f"Finish reason for {image_path}: {reason_text}")

                    if finish_reason == 1:  # STOP is normal
                        extracted_text = candidate.content.parts[0].text
                        error_handled = False  # Ensure we mark it as not an error
                    elif finish_reason in finish_reason_dict:
                        error_handled = True
                        print(f"{reason_text} for {image_path}.")
                        print(json.dumps(MessageToDict(response), indent=2))
                        log_unfinished_file_csv(csv_path, image_path, reason_text)  
                        print("Logging to csv file.")
                    else:
                        print(f"Unhandled finish reason ({finish_reason}) for {image_path}.")
                        print(json.dumps(MessageToDict(response), indent=2))
                else:
                    print(f"Failed to extract text for {image_path}. No valid candidates returned.")
                    error_handled = True

            except StopCandidateException as sce:
                # Access the candidate from the exception's arguments
                candidate = sce.args[0]  # The candidate is passed as the first argument
                finish_reason = candidate.finish_reason
                reason_text = finish_reason_dict.get(finish_reason, f"Unknown finish reason ({finish_reason})")

                print(f"Handled StopCandidateException for {image_path}: {sce}")
                print(f"Finish reason: {reason_text}")

                # Log the unfinished file
                log_unfinished_file_csv(csv_path, image_path, reason_text)
                error_handled = True

            except Exception as e:
                print(f"An error occurred while processing {image_path}: {e}")
                print(traceback.format_exc())  # Print the full stack trace
                error_handled = True  # Mark the error as handled

                if "429" in str(e):
                    print(f"Rate limit error for {image_path}. Exiting.")
                    sys.exit()
                else:
                    print(f"Unexpected error: {e}")

            if not error_handled:
                print(f"Failed to process {image_path} due to an unexpected error.")

            if extracted_text:
                with open(output_file, "w") as f:
                    f.write(extracted_text)
                print("*"*100)
                print(f"Saved text output to {output_file}")
                print(extracted_text)
                print("*"*100)
                processed_files += 1
            else:
                print(f"No text extracted for {image_path}\n")

    print(f"Total files: {total_files}")
    print(f"Processed files: {processed_files}")
def main():
    # Directory containing PNG files
    image_directory = "./output_images/"
    output_directory = "./output_text/"
    csv_path = "./unfinished_files.csv"

    # Load unfinished files from CSV
    unfinished_files = load_unfinished_files(csv_path)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    process_images(image_directory, output_directory, unfinished_files, csv_path)

if __name__ == "__main__":
    main()
