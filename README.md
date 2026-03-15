# G-WaB: Geographic Water Budget

Field-scale crop water budgeting from satellite-derived climate and vegetation signals.

This Streamlit app estimates seasonal irrigation needs using:
- NDVI from Sentinel-2
- Rainfall from CHIRPS
- ET0 from TerraClimate

![Example](img/ExampleGraph.png)

## Authors

Or Sperling, Zac Ellis, Niccolò Tricerri, Maciej Zwieniecki

## App entrypoint

- Main app: `GWaB_app.py`

## Local setup

1. Create and activate a Python 3.11+ environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run GWaB_app.py
```

## Earth Engine authentication

The app supports two auth modes:

### A) Streamlit Cloud / deployed app

Set Streamlit secrets with a service account JSON dictionary under `gcp_service_account`.
Optional: set `gcp_project` (defaults to `rsc-gwab-lzp`).

Example `.streamlit/secrets.toml` content:

```toml
gcp_project = "your-gcp-project-id"

[gcp_service_account]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

### B) Localhost

Use one of these:
- `earthengine authenticate`
- Application Default Credentials
- Existing default EE credentials

If no valid credentials are found, the app raises a clear initialization error.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. Create a new Streamlit app from the GitHub repo.
3. Set:
	- Branch: `main`
	- Main file path: `GWaB_app.py`
4. Add secrets (`gcp_service_account`, optionally `gcp_project`).
5. Deploy.

## Notes

- Region switch (Israel/California) is controlled in the sidebar.
- Map uses Google satellite tiles only.
