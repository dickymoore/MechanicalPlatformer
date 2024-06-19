import json
import os
import subprocess
from datetime import datetime
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
                {"role": "user", "content": "Can you confirm that the OpenAI API key is working?"}
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

# Function to generate code based on an intent
def generate_code(intent):
    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
    )

    description = intent['description']
    test = intent['test']

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a Terraform and Python expert."},
            {"role": "user", "content": f"Provide Terraform code to {description} and Python code to test it. The test should verify: {test}"}
        ]
    )

    message_content = response.choices[0].message.content
    parts = message_content.split("```")

    terraform_code = parts[1].strip() if "terraform" in parts[1] else ""
    test_code = parts[3].strip() if "python" in parts[3] else ""

    intent_id = intent['id']
    os.makedirs(f'terraform/{intent_id}', exist_ok=True)
    with open(f'terraform/{intent_id}/main.tf', 'w') as f:
        f.write(terraform_code)

    os.makedirs(f'test/{intent_id}', exist_ok=True)
    with open(f'test/{intent_id}/test_{intent_id}.py', 'w') as f:
        f.write(test_code)

# Function to update the status of an intent
def update_intent_status(intents, intent_id, status):
    for intent in intents['intents']:
        if intent['id'] == intent_id:
            intent['status'] = status
            intent['updated_at'] = datetime.utcnow().isoformat() + 'Z'
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
            generate_code(intent)
            commit_changes(intent_id)

            # Apply Terraform configuration
            result = subprocess.run(f"cd terraform/{intent_id} && terraform init && terraform apply -auto-approve", shell=True)
            if result.returncode != 0:
                print(f"Terraform apply failed for {intent_id}")
                continue

            # Run tests
            result = subprocess.run(f"python test/{intent_id}/test_{intent_id}.py", shell=True)
            if result.returncode == 0:
                print(f"Intent '{intent['description']}' fulfilled.")
                update_intent_status(intents, intent_id, 'fulfilled')
                save_intents(intents_file, intents)

                # Create metadata file to indicate fulfillment
                with open(f'terraform/{intent_id}/intent_fulfilled.json', 'w') as f:
                    json.dump({"fulfilled": True, "timestamp": datetime.utcnow().isoformat() + 'Z'}, f, indent=4)
            else:
                print(f"Intent '{intent['description']}' not fulfilled. Check the logs for details.")
                update_intent_status(intents, intent_id, 'pending')

if __name__ == "__main__":
    main()