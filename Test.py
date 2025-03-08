from AIFeatures import AIFeatures
from AIFlashcards import AIFlashcards
from AISummary import AISummary
from AIQuestions import AIQuestions

# Replace with your actual API key
API_KEY = 'AIzaSyCFP_xnzpKf8FBn7Nl1cqOU682IicQykLg'

# Create an instance of AIFeatures
ai_features = AIFeatures(API_KEY,"C:/Users/gill_/Desktop/notes2.pdf")
#print(ai_features.uploaded_file)
flashcards = AIFlashcards(ai_features)
summary = AISummary(ai_features)
questions = AIQuestions(ai_features, 5)
#print(flashcards.uploaded_file)
result = questions.generate_content()
print(result)

parsed_questions = questions.parse_output(result)
for question in parsed_questions:
    print("Here")
    print(f"{question['question_number']}. {question['question']}")
    print(f"a. {question['options']['a']}")
    print(f"b. {question['options']['b']}")
    print(f"c. {question['options']['c']}")
    print(f"d. {question['options']['d']}")
    print() 



# Set a file path (ensure this file exists)
#ai_features.set_file("C:/Users/gill_/Desktop/notes.pdf")  # Replace with a valid file path
'''
# Create an instance of AIFlashcards using the AIFeatures instance
flashcards = AIFlashcards(ai_features)
summary = AISummary(ai_features)
questions = AIQuestions(ai_features, 5)
generated_text = questions.generate_content()
print("\nGenerated Content:\n", generated_text)
# Run the generate_content method and print output
#generated_text = flashcards.generate_content()
#flashcards_dict = flashcards.create_dict(generated_text)

#print(flashcards.get_word(flashcards_dict["2"]) + " - " + flashcards.get_def(flashcards_dict["2"]))
#for key, value in flashcards_dict.items():
#    print(f"{key}: {value['word']} - {value['definition']}")
#print("\nGenerated Content:\n", generated_text)

#delete files every time.'
'''
ai_features.delete_all_files()
