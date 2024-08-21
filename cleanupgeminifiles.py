import os
import google.generativeai as genai

# Configure the Gemini API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def list_gemini_files():
    """Lists the files uploaded to your Gemini AI account."""
    try:
        # Call the API to list files
        files = list(genai.list_files())  # Converting the generator to a list
        
        if files:
            print(f"Total files found: {len(files)}")
            for idx, file in enumerate(files):
                print(f"{idx + 1}. File URI: {file.uri}, Display Name: {file.display_name}, Size: {file.size_bytes} bytes, Created: {file.create_time}")
            return files
        else:
            print("No files found.")
            return []
    except Exception as e:
        print(f"Failed to list files: {e}")
        return []

def delete_gemini_file(file_uri):
    """Deletes a file from Gemini AI using its URI."""
    try:
        # Extract the file ID from the URI
        file_id = file_uri.split('/')[-1]

        # Call the delete_file method with only the file ID
        genai.delete_file(file_id)
        print(f"Deleted file with URI: {file_uri}")
    except Exception as e:
        print(f"Failed to delete file with URI {file_uri}: {e}")

def cleanup_gemini_files():
    """Lists and deletes all files from Gemini AI after user confirmation."""
    # List all files
    files = list_gemini_files()

    if not files:
        print("No files to delete.")
        return

    # Ask for user confirmation
    confirm = input("Do you want to delete all these files? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        print("Deleting files...")
        for file in files:
            delete_gemini_file(file.uri)
        print("All files deleted.")
    else:
        print("Operation canceled. No files were deleted.")

if __name__ == "__main__":
    cleanup_gemini_files()
