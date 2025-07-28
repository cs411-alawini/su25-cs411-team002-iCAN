# README for Team iCAN
## Testing on your computer
Below are instructions on how to test this on your computer. The code is written below and begins with a dollar sign ($). Do not copy the dollar sign. Please copy all the code after the dollar sign, but do not include the dollar sign in the code.

1. Activate the virtual environment:
$ source .venv/bin/activate

2. Download dependencies:
$



3. Copy paste:
export INSTANCE_CONNECTION_NAME="my-gcp-project:us-central1:my-sql-instance"
export DB_USER="hannahk8"
export DB_PASS="hannahk8"
export DB_NAME="pokemon_battle_db"

4. Get to the backend directory
$ cd backend

6. Grab the key to our GCP 


1. Navigate to this site: https://cloud.google.com/sdk/docs/install

2. Determine which version you have
$ uname -m

3. Download that platform's package


cd to downloads
tar -xf google-cloud-cli-darwin-arm.tar.gz

./google-cloud-sdk/install.sh

./google-cloud-sdk/bin/gcloud init

python -m venv .venv
source .venv/bin/activate

cd backend

pip install -r requirements.txt

go to root folder
touch .env

inside .env
INSTANCE_CONNECTION_NAME="cs411-team002-ican:us-central1:cs411-team002-ican"
(Change with your username)
DB_USER="hannahk8"
(Change with your password)
DB_PASS="hannahk8"
DB_NAME="pokemon_battle_db"


gcloud auth application-default login 

cd backend
python run.py





# maybe???? --> pip install urllib3==1.26.15