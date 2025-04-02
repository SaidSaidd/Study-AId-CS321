# Study-AId-CS321

Note for team: To test, you must first install the google-genai package. To do so, make sure Python is installed on your device. Navigate to C:\Users\Your Name\AppData\Local\Programs\Python in terminal. Perform ls to check your Python version. Then type cd PythonVersion\Scripts. Then istall the package by typing ./pip install -q -U google-genai. You should be able to run the code once the package is installed. **Ignore the warnings**

Note on adding file path manually during testing: Python will interpret the '\' symbol as the start of an escape sequence. When adding a file path, make sure you use '/' or you will get errors. This may differ on non-Windows devices. If you get an error like this, the path is being interpreted as an escape sequence:\
\
     SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 2-3: truncated \UXXXXXXXX escape\
     \
Additionally, make sure to provide the complete file path from the root directory. 


Use test_all_classes.py to test any new code. Try not adding test code to the class files themselves.



Instructions to run front end:
Firstly, you must install firebase-admin. navigate to C:\Users\Your Name\AppData\Local\Programs\Python\Python313\Scripts and run the command ./pip install firebase-admin.
Next, from the same directory, install Flask by typing ./pip install Flask.

From there, run the app.py file to run the webpage locally.
