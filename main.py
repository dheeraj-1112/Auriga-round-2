"""Entry point for the gift_pool application.

Run with:  python3 main.py
Then open http://127.0.0.1:5000 in a browser.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
