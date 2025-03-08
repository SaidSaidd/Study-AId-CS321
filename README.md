# Study-AId-CS321

Note for team: To test, you must first install the google-genai package. To do so, make sure Python is installed on your device. Navigate to C:\Users\Your Name\AppData\Local\Programs\Python in terminal. Perform ls to check your Python version. Then type cd PythonVersion\Scripts. Then istall the package by typing ./pip install -q -U google-genai. You should be able to run the code once the package is installed. **Ignore the warnings**

Note on adding file path manually during testing: Python will interpret the '\' symbol as the start of an escape sequence. When adding a file path, make sure you use '/' or you will get errors. This may differ on non-Windows devices. If you get an error like this, the path is being interpreted as an escape sequence:\
\
     SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 2-3: truncated \UXXXXXXXX escape\
     \
Additionally, make sure to provide the complete file path from the root directory. 


Use Test.py to test any new code. Try not adding test code to the class files themselves.
