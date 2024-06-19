import json
import os
import subprocess
from datetime import datetime, timezone
import requests
import openai
from openai import OpenAI

# Function to load and validate OpenAI API key
def load_and_validate_openai_api_key():
    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
    )
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello. Just checking that I am correctly connecting with you."}
            ]
        )
        print("OpenAI API key is valid. Test response:", response.choices[0].message.content)
    except Exception as e:
        raise ValueError(f"Failed to validate OpenAI API key: {e}")

# Function to load intents from a file
def load_intents(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Function to save intents to a file
def save_intents(file_path, intents):
    with open(file_path, 'w') as f:
        json.dump(intents, f, indent=4)

def remove_backticks(code):
    return code.replace("```", "")

def extract_code_between_keywords(response, start_keyword, end_keyword):
    start = response.find(start_keyword) + len(start_keyword)
    end = response.find(end_keyword)
    if start < len(start_keyword) or end == -1:
        return ""
    return response[start:end].strip()


# Function to generate Terraform code based on an intent
def generate_terraform_code(intent):
    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
    )

    description = intent['description']

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a Terraform expert."},
            {"role": "user", "content": f"Provide Terraform code to {description}. The code must be ready to run immediately without me making any changes. I have these environment variables set: AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY, AWS_REGION. If you need a name for this project, it's: MechanicalPlatform-{intent['id']}. Please include the Terraform code between the keywords 'BEGIN_TERRAFORM_CODE' and 'END_TERRAFORM_CODE'."}
        ]
    )

    message_content = response.choices[0].message.content
    print("ChatGPT response for Terraform code:", message_content)

    # Extract the Terraform code block
    terraform_code = extract_code_between_keywords(message_content, "BEGIN_TERRAFORM_CODE", "END_TERRAFORM_CODE")

    # Remove backticks from the extracted code
    terraform_code = remove_backticks(terraform_code)

    if not terraform_code:
        raise ValueError("Terraform code not found in the response.")

    intent_id = intent['id']
    os.makedirs(f'terraform/{intent_id}', exist_ok=True)
    with open(f'terraform/{intent_id}/main.tf', 'w') as f:
        f.write(terraform_code)

# Function to generate test code based on an intent
def generate_test_code(intent):
    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
    )

    test = intent['test']

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a Python expert."},
            {"role": "user", "content": f"Provide Python code to test the following: {test}. The code must be ready to run immediately without me making any changes. Please respond with only the Python code between the delimiters START_CODE and END_CODE."}
        ]
    )

    message_content = response.choices[0].message.content
    print("ChatGPT response for test code:", message_content)  # Debugging output

    test_code = extract_code_between_delimiters(message_content, "START_CODE", "END_CODE")

    if not test_code:
        raise ValueError("Python test code not found in the response.")

    intent_id = intent['id']
    os.makedirs(f'test/{intent_id}', exist_ok=True)
    with open(f'test/{intent_id}/test_{intent_id}.py', 'w') as f:
        f.write(test_code)

def extract_code_between_delimiters(response, start_delimiter, end_delimiter):
    start = response.find(start_delimiter) + len(start_delimiter)
    end = response.find(end_delimiter)
    if start < len(start_delimiter) or end == -1:
        return ""
    return response[start:end].strip()

# Function to update the status of an intent
def update_intent_status(intents, intent_id, status):
    for intent in intents['intents']:
        if intent['id'] == intent_id:
            intent['status'] = status
            intent['updated_at'] = datetime.now(timezone.utc).isoformat()
            break

# Function to set up and switch to a new branch for the intent
def setup_branch(intent_id):
    branch_name = f"intent-{intent_id}"
    current_branch = subprocess.check_output(["git", "branch", "--show-current"]).strip().decode('utf-8')
    if current_branch != branch_name:
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    else:
        subprocess.run(["git", "checkout", branch_name], check=True)

# Function to commit changes to the branch
def commit_changes(intent_id):
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Add code for intent {intent_id}"], check=True)
    subprocess.run(["git", "push", "-u", "origin", f"intent-{intent_id}"], check=True)

# Main function
def main():
    load_and_validate_openai_api_key()
    intents_file = 'intents.json'
    intents = load_intents(intents_file)

    for intent in intents['intents']:
        if intent['status'] == 'pending':
            print(f"Processing intent: {intent['description']}")
            intent_id = intent['id']

            setup_branch(intent_id)
            generate_terraform_code(intent)
            exit()
            generate_test_code(intent)
            commit_changes(intent_id)

            # # Apply Terraform configuration
            # result = subprocess.run(f"cd terraform/{intent_id} && terraform init && terraform apply -auto-approve", shell=True)
            # if result.returncode != 0:
            #     print(f"Terraform apply failed for {intent_id}")
            #     continue

            # # Run tests
            # result = subprocess.run(f"python test/{intent_id}/test_{intent_id}.py", shell=True)
            # if result.returncode == 0:
            #     print(f"Intent '{intent['description']}' fulfilled.")
            #     update_intent_status(intents, intent_id, 'fulfilled')
            #     save_intents(intents_file, intents)

            #     # Create metadata file to indicate fulfillment
            #     with open(f'terraform/{intent_id}/intent_fulfilled.json', 'w') as f:
            #         json.dump({"fulfilled": True, "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=4)
            # else:
            #     print(f"Intent '{intent['description']}' not fulfilled. Check the logs for details.")
            #     update_intent_status(intents, intent_id, 'pending')

if __name__ == "__main__":
    main()
