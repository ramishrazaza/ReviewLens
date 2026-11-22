"""Safely create an ignored local .env file for Gemini credentials."""
import os
from getpass import getpass
from pathlib import Path


def main():
    target = Path(__file__).resolve().parent / '.env'
    if target.exists():
        print('Private .env already exists; edit that file if you need to change your key.')
        return
    key = getpass('Enter your Gemini API key (hidden, never committed): ').strip()
    if not key or any(c in key for c in '\r\n\x00'):
        raise ValueError('An API key is required and must occupy one line.')
    data = ('GEMINI_API_KEY=' + key + '\n'
            'GEMINI_MODEL=gemini-3.5-flash-lite\n'
            'REVIEWLENS_DEMO_MODE=0\nPORT=8000\n')
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as file:
        file.write(data)
    print('Saved the key privately in .env (excluded by .gitignore).')
    print('Now run: python run.py')


if __name__ == '__main__':
    main()
