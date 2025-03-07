from AIFeatures import AIFeatures
from AIFlashcards import AIFlashcards

# Replace with your actual API key
API_KEY = 'AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg'

# Create an instance of AIFeatures
ai_features = AIFeatures(api_key=API_KEY)

# Set a file path (ensure this file exists)
ai_features.set_file("")  # Replace with a valid file path

# Create an instance of AIFlashcards using the AIFeatures instance
flashcards = AIFlashcards(ai_features)

# Print copied attributes
print(f"File Path in Flashcards: {flashcards.file_path}")
print(f"Client Object in Flashcards: {flashcards.client}")

# Run the generate_content method and print output
print("\nGenerating content from AIFlashcards...")
generated_text = flashcards.generate_content()
print("\nGenerated Content:\n", generated_text)

ai_features.delete_all_files()
flashcards.delete_all_files()
