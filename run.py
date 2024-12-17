from app import create_app

# Create an instance of the Flask app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2010, debug=True)