import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service_for_account(account_name):
    """
    Authenticates and builds a Gmail service instance for a specific account.
    """
    creds = None
    token_file = f'token_{account_name}.json'

    # Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If credentials are not valid or missing, request interactive log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save credentials for future execution
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

# --- Main Usage ---
if __name__ == "__main__":
    accounts = ['rodriguesjosepedro407@gmail.com', 'zepedromartinsrodrigues@gmail.com', 'josepmartrodrigues@gmail.com']

    for acc in accounts:
        print(f"\n--- Fetching profile for: {acc} ---")
        service = get_gmail_service_for_account(acc)
        
        # Query the Gmail API
        profile = service.users().getProfile(userId='me').execute()
        print(f"Connected Email: {profile['emailAddress']}")
        print(f"Total Messages: {profile['messagesTotal']}")