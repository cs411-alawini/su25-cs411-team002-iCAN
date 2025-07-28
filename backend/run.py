from app import create_app

# Create the Flask app instance using the factory
app = create_app()

# Runs when 'python run.py' is ran in the terminal
if __name__ == '__main__':
    app.run(debug=True) # Start the development server 
     