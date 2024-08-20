import os
import sys
import google.generativeai as genai
import json
from google.protobuf.json_format import MessageToDict

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

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini and returns the file metadata."""
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        print(f"Failed to upload file {path}: {e}")
        return None

def process_images(directory, output_directory):
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

            image_path = os.path.join(root, image_file)
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

                    if finish_reason == 1:  # STOP
                        extracted_text = candidate.content.parts[0].text
                    elif finish_reason in finish_reason_dict:
                        error_handled = True
                        print(f"{reason_text} for {image_path}.")
                        print(json.dumps(MessageToDict(response), indent=2))
                    else:
                        print(f"Unhandled finish reason ({finish_reason}) for {image_path}.")
                        print(json.dumps(MessageToDict(response), indent=2))
                else:
                    print(f"Failed to extract text for {image_path}. No valid candidates returned.")
                    error_handled = True

            except Exception as e:
                if "429" in str(e):
                    print(f"Failed to process {image_path} due to rate limiting. Sleeping for 60 seconds.")
                    sys.exit()
                else:
                    print(f"An error occurred: {e}")
                    if "RECITATION" in str(e):
                        error_handled = True

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

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    process_images(image_directory, output_directory)

if __name__ == "__main__":
    main()
