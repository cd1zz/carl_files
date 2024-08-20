import os
import spacy
from collections import defaultdict

# Load SpaCy's pre-trained NER model
nlp = spacy.load("en_core_web_sm")

# Define the root directory containing subfolders with text files
root_directory = "./output_text"

# Define output file
output_file = "./output_entities/entities_by_type.txt"

# Function to process a single text file and extract entities with metadata
def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        doc = nlp(text)

        entities_with_metadata = []
        for ent in doc.ents:
            # Capture entity text, label, and context (file path and position)
            entity_data = {
                "entity": ent.text,
                "label": ent.label_,
                "file_path": file_path,
                "start_char": ent.start_char,
                "end_char": ent.end_char
            }
            entities_with_metadata.append(entity_data)
        
        return entities_with_metadata
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return []

# Function to process all text files in a directory (including subdirectories)
def process_directory(directory_path):
    all_entities = []

    for subdir, _, files in os.walk(directory_path):
        print(f"Processing {subdir}")
        for file in files:
            if file.endswith('.txt'):
                file_path = os.path.join(subdir, file)
                entities = process_file(file_path)
                
                # Add entities from the current file to the overall collection
                all_entities.extend(entities)
    
    return all_entities

# Function to handle file output
def write_to_output_file(output_file, entities_with_metadata):
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write the entities with metadata to the output file
        with open(output_file, 'w', encoding='utf-8') as f:
            for entity_data in entities_with_metadata:
                f.write(f"Entity: {entity_data['entity']}, Label: {entity_data['label']}, "
                        f"File: {entity_data['file_path']}, "
                        f"Position: ({entity_data['start_char']}, {entity_data['end_char']})\n")
        print(f"Entities successfully written to {output_file}")
    except Exception as e:
        print(f"Error writing to file {output_file}: {e}")

# Run the processing on the root directory
entities_with_metadata = process_directory(root_directory)

# Write the results to the output file
write_to_output_file(output_file, entities_with_metadata)