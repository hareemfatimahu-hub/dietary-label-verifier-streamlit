DIETARY LABEL & RECIPE VERIFIER - PRIVATE BETA PACKAGE

FILES
app.py                   the app
requirements.txt         Python packages
packages.txt             installs the OCR engine on the server
.streamlit/config.toml   limits uploads to 5 MB

BEFORE YOU DEPLOY
1. Open app.py and change CONTACT_EMAIL near the top to an email made for this project.
2. Do not add your employer's name, logo, or your clinical title anywhere in the app.

DEPLOY (free)
1. Create a free GitHub account and a PRIVATE repository.
2. Upload every file in this folder, including the .streamlit folder.
3. Go to share.streamlit.io, sign in with GitHub, click New app, pick the repository,
   set main file to app.py, and click Deploy.
4. Open the app Settings, then Sharing. Make the app private and add the emails of the
   people allowed to view it. Options may be worded differently, so read the page.
5. Test with five packs on the live link before inviting anyone.

RUN ON YOUR OWN COMPUTER INSTEAD
Install Python and Tesseract (with Urdu data), then:
pip install -r requirements.txt
streamlit run app.py

KEEP IT SAFE
- Private beta only. Do not post the link publicly or to patients.
- Rules lists are UNVERIFIED starter lists. Check each against EFSA, Codex INS and PSQCA,
  then set RULES_VERSION in app.py to a real date.
- Test 30 real packs you read by hand first. Log every miss and fix the lists.
- Never change result wording to say safe, Halal, gluten free or diabetic friendly.
- Read your employment contract on outside work before sharing this widely.
- Get advice from a technology lawyer and consider liability insurance before any public launch.
