import os
import openai
import csv
import traceback

# Configure OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def log_unfinished_file_csv(csv_path, file_path, finish_reason):
    with open(csv_path, "a", newline='') as csvfile:
        log_writer = csv.writer(csvfile)
        log_writer.writerow([file_path, finish_reason])

def load_unfinished_files(csv_path):
    unfinished_files = {}
    if os.path.exists(csv_path):
        with open(csv_path, "r") as csvfile:
            log_reader = csv.reader(csvfile)
            for row in log_reader:
                if len(row) > 0:
                    unfinished_files[row[0]] = row[1]
    return unfinished_files

def process_images(csv_path, output_directory):
    unfinished_files = load_unfinished_files(csv_path)
    
    for image_path, reason in unfinished_files.items():
        text_root = os.path.join(output_directory, os.path.dirname(os.path.relpath(image_path, start="./output_images")))
        os.makedirs(text_root, exist_ok=True)
        output_file = os.path.join(text_root, f"{os.path.basename(image_path)[:-4]}.txt")
        
        # Check if the corresponding text file already exists
        if os.path.exists(output_file):
            print(f"Skipping {image_path}, corresponding text file already exists.")
            continue

        try:
            print(f"Processing: {image_path}")

            # Upload the image file to OpenAI
            with open(image_path, "rb") as image_file:
                file_response = openai.File.create(
                    file=image_file,
                    purpose="vision"
                )
                file_id = file_response['id']

            # Create a user message with the file ID
            response = openai.ChatCompletion.create(
                model="gpt-4-vision",
                messages=[
                    {"role": "user", "content": "Please analyze this image.", "file": {"id": file_id}}
                ]
            )

            # Extract text from the response
            extracted_text = response['choices'][0]['message']['content']

            # Save the extracted text to a file
            with open(output_file, "w") as f:
                f.write(extracted_text)
            print(f"Saved text output to {output_file}")
        
        except Exception as e:
            print(f"An error occurred while processing {image_path}: {e}")
            print(traceback.format_exc())
            log_unfinished_file_csv(csv_path, image_path, str(e))  # Log the error reason

def main():
    csv_path = "./unfinished_files.csv"
    output_directory = "./output_text/"

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    process_images(csv_path, output_directory)

if __name__ == "__main__":
    main()
