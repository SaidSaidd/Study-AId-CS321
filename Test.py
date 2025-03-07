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

# Run the generate_content method and print output
generated_text = flashcards.generate_content()
flashcards_dict = flashcards.create_dict(generated_text)

for key, value in flashcards_dict.items():
    print(f"{key}: {value['word']} - {value['definition']}")
#print("\nGenerated Content:\n", generated_text)

#delete files every time.
ai_features.delete_all_files()
flashcards.delete_all_files()
