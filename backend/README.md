# README for Team iCAN

## Setting up Flask and GCP - Only need to do once
Below are instructions on how to test this on your computer. The code is written below and begins with a dollar sign ($). Do not copy the dollar sign. Please copy all the code after the dollar sign, but do not include the dollar sign in the code.


1. Navigate to this site: https://cloud.google.com/sdk/docs/install

2. Determine which version you have
$ uname -m

3. Download that platform's package

4. In terminal, get to the Downloads directory
$ cd Downloads

5. Once you're in the Downloads directory, run the following code:
$ tar -xf google-cloud-cli-darwin-arm.tar.gz

6. Run this
$ ./google-cloud-sdk/install.sh

7. Then, run this
$ ./google-cloud-sdk/bin/gcloud init

8. Create a virtual environment
$ python -m venv .venv

9. Activate your virtual environment
$ source .venv/bin/activate

10. Navigate to the root folder (make sure you are in "su25-cs411-team002-iCAN")

11. Install the dependencies
$ pip install -r requirements.txt


12. Create a .env file. This is where your GCP credentials will go.
$ touch .env

13. Open your .env file and copy the information below

INSTANCE_CONNECTION_NAME="cs411-team002-ican:us-central1:cs411-team002-ican"
DB_USER="hannahk8" --- Replace this with your username
DB_PASS="hannahk8" --- Replace this with your password
DB_NAME="pokemon_battle_db"


14. Run the following command in your terminal:
$ gcloud auth application-default login 

15. Navigate to the backend folder
$ cd backend

16. Run the flask app!
$ python run.py


## Test your flask app

1. Activate virtual environment
$ source .venv/bin/activate

2. Navigate to backend folder
$ cd backend

3. Run flask app
$ python run.py