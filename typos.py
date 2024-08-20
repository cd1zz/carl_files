import os
import re

def replace_in_file(filename, replacements, counts):
    with open(filename, 'r') as file:
        content = file.read()

    for old, new in replacements:
        # Count occurrences before replacing
        occurrences = len(re.findall(old, content))
        counts[old] += occurrences
        
        # Perform the replacement
        content = re.sub(old, new, content)

    with open(filename, 'w') as file:
        file.write(content)

def process_directory(directory, replacements):
    counts = {old: 0 for old, _ in replacements}
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.txt'):  # Adjust this if you want to include other file types
                file_path = os.path.join(root, file)
                replace_in_file(file_path, replacements, counts)

    return counts

# List of replacements: (pattern, replacement)
replacements = [
    (r'CARL N\. FREEMAN', 'CARL N. FREYMAN'),
    (r'\b[Rr][Uu][Ee][Yy]\b', 'RUBY'),
    (r'CARL H\. FREEMAN', 'CARL N. FREYMAN'),
    (r'CARL NICHOLAS FREEMAN', 'CARL NICHOLAS FREYMAN'),
    (r'CARL M\. FREEMAN', 'CARL N. FREYMAN')
]

# Example usage: replace 'your_directory' with the actual directory you want to process
directory = '/home/user/carl_files/output_text/'
counts = process_directory(directory, replacements)

# Print out the number of occurrences for each regular expression
print(f"Processed {directory}")
for pattern, count in counts.items():
    print(f"Pattern '{pattern}' was used {count} time(s).")
