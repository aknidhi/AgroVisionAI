AGROVISION AI — STREAMLIT COMMUNITY CLOUD DEPLOYMENT SOURCE

Sanitized deployment copy of the latest tested project.

SECURITY:
- The real .env is deliberately excluded.
- .venv, __pycache__, .vscode and data/cache are excluded.
- .gitignore excludes .env and .env.*.
- Never upload real API keys to GitHub.

PREPARE:
1. Extract this ZIP.
2. Upload the contents of the AgroVisionAI folder to a GitHub repository.
3. Confirm streamlit_app.py and requirements.txt are in the repository root.
4. Do not upload .env.
5. Add the five secrets from .env.example to Streamlit Community Cloud app settings.

SECRETS:
The app entrypoint bridges st.secrets values into environment variables because
the existing services read credentials with os.getenv(). In Community Cloud,
paste the TOML values from .env.example into Advanced settings -> Secrets,
replacing placeholders with real keys.

DEPENDENCIES:
requirements.txt includes Pillow and reportlab required by image processing
and PDF report features.

DEPLOY:
- Repository: your AgroVision AI GitHub repository
- Branch: main
- Main file path: streamlit_app.py
- Python: 3.12
