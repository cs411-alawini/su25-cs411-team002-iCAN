# Testing on your computer
Below are instructions on how to test this on your computer. The code is written below and begins with a dollar sign ($). Do not copy the dollar sign. Please copy all the code after the dollar sign, but do not include the dollar sign in the code.

1. Activate the virtual environment:
$ source .venv/bin/activate

2. Download dependencies:
$


cloud init
cloud auth login
clou
3. Copy paste:
export INSTANCE_CONNECTION_NAME="my-gcp-project:us-central1:my-sql-instance"
export DB_USER="hannahk8"
export DB_PASS="hannahk8"
export DB_NAME="pokemon_battle_db"

4. Get to the backend directory
$ cd backend

6. Grab the key to our GCP 


7. Download JSON and get the file directory
$export GOOGLE_APPLICATION_CREDENTIALS="/Users/hannahkim/Desktop/CS 411 SU25/Pokemon Project/cs411-team002-ican-105b9158fa75.json"

Run the flask debugging command:
$ flask --app app --debug run

https://cloud.google.com/sdk/docs/install
uname -m

download that platform's package

cd to downloads
tar -xf google-cloud-cli-darwin-arm.tar.gz

./google-cloud-sdk/install.sh

./google-cloud-sdk/bin/gcloud init

python -m venv .venv
source .venv/bin/activate

cd backend

pip install -r requirements.txt

go to root
touch .env

inside .env
INSTANCE_CONNECTION_NAME="cs411-team002-ican:us-central1:cs411-team002-ican"
DB_USER=“hannahk8”
DB_PASS=“hannahk8”
DB_NAME="pokemon_battle_db"



gcloud auth application-default login 

cd backend
python run.py





# maybe???? --> pip install urllib3==1.26.15