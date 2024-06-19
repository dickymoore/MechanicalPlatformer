python
import boto3
import datetime
from botocore.exceptions import NoCredentialsError

def upload_to_aws(local_file, bucket, s3_file):
    s3 = boto3.client('s3')

    try:
        s3.upload_file(local_file, bucket, s3_file)
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

date = datetime.datetime.now().strftime('%Y-%m-%d')
filename = '/path/to/your/index.html'
content = f"<h1>Hello! I have been made automatically on {date} by ChatGPT based on instructions from Dicky Moore.</h1>"

with open(filename, 'w') as f:
    f.write(content)

uploaded = upload_to_aws('index.html', '<your_bucket_name>', 'index.html')