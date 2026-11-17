# Publish FastRoute to GitHub

This ZIP contains the current FastRoute project source without the local Python virtual environment, temporary caches, or backups.

## On iPhone (GitHub website)
1. Sign in to https://github.com and create a new repository named `FastRoute` (choose **Public** if your instructor must open it without a login).
2. Leave **Add a README**, **.gitignore**, and **license** unchecked during creation; the project already includes a README and .gitignore. Do not choose a license unless your group has agreed to one.
3. GitHub's browser file uploader cannot upload this ZIP as an expanded repository. To upload its contents, extract the ZIP using Files, then upload the extracted project files through GitHub's **Add file → Upload files** page. On iPhone, uploading many nested files may be difficult; a computer is strongly recommended.
4. On a Windows computer, the easiest method is GitHub Desktop: create a repository from the extracted FastRoute folder, then Publish repository. Confirm `.venv`, `cache`, `backups` and secrets are not included.
5. Copy the final link `https://github.com/YOUR-USERNAME/FastRoute` and submit it with all group members' names.

## Run on Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Run tests
```powershell
python -m unittest discover -s tests -v
```

## Submission details
- Group project: FastRoute — Interactive Delivery Route Algorithm Visualization
- Course: CPS 3440 — Analysis of Algorithms
- Group members: **add every group member's full name**
- Web repository: **paste your real GitHub URL after publishing**

Do not claim a GitHub repository exists until it has been published and the URL verified.
