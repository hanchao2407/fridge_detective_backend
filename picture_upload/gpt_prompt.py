from PIL import Image
import base64
import requests
import os
from dotenv import load_dotenv
import json
import time
from concurrent.futures import ThreadPoolExecutor  # Import ThreadPoolExecutor
from openai import OpenAI
import re


# Load the environment variables from the .env file
load_dotenv()

# Access the OPENAI_API_KEY
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def resize_image(image_path, max_width=500):
    with Image.open(image_path) as img:
        print("Image pixels: " +  str(img.size))
        file_size = os.path.getsize(image_path)
        print(f"File size: {file_size} bytes")
        # Calculate the height using the aspect ratio
        ratio = max_width / img.width
        new_height = int(img.height * ratio)

        # Resize the image using LANCZOS resampling filter
        resized_img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Prepare the directory for the resized image
        resized_dir = "resized_uploaded_images"
        if not os.path.exists(resized_dir):
            os.makedirs(resized_dir)

        # Save the resized image
        resized_image_path = os.path.join(resized_dir, os.path.basename(image_path))
        resized_img.save(resized_image_path)

        return resized_image_path

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def generate_images(prompts):
    def generate_image(prompt):
        # Assuming the 'client.images.generate' function and its parameters are defined elsewhere
        response = client.images.generate(
            # model="dall-e-2",
            prompt=prompt,
            size="512x512",
            # quality="standard",
            # style='vivid',
            n=1,
        )
        
        return response.data[0].url

    # Start timing
    # start_time = time.time()

    # Use ThreadPoolExecutor to run requests concurrently
    with ThreadPoolExecutor(max_workers=len(prompts)) as executor:
        # Create a list of future objects for each prompt
        futures = [executor.submit(generate_image, prompt) for prompt in prompts]

        # Wait for all futures to complete and get the results
        image_urls = [future.result() for future in futures]

    # End timing
    # end_time = time.time()

    # Calculate duration
    # duration = end_time - start_time

    return image_urls

def generate_recipe_from_image(image_path,recipe_amount,generate_with_image,language='english'):
    # print(image_path)
    resized_image_path = resize_image(image_path)
    base64_image = encode_image(resized_image_path)
    # language = 'english'
    recipe_request_1 = 'generate ' + recipe_amount +' recipe based on ingredients on the picture and purely return in '+ language+ ' in json format as [{"title":"","shortdescription":"shortdescription", "preptime":"minutes","ingredients":[[ingredient, amount as string]], "instructions":[]}]'
    recipe_request_2 = 'generate ' + recipe_amount +' cooking recipe based on ingredients detected on the picture and purely return in '+ language+ ' in json format as [{"title":"","shortdescription":"shortdescription", "preptime":"minutes","ingredients":[[ingredient, amount as string]], "instructions":[]}]'
    recipe_request_3 = 'generate ' + recipe_amount +' food recipe based on the groceries on the picture and purely return in '+ language+ ' in json format as [{"title":"","shortdescription":"shortdescription", "preptime":"minutes","ingredients":[[ingredient, amount as string]], "instructions":[]}]'
    recipe_request_4 = 'generate ' + recipe_amount +' tasty recipe based on the items on the picture and purely return in '+ language+ ' in json format as [{"title":"","shortdescription":"shortdescription", "preptime":"minutes","ingredients":[[ingredient, amount as string]], "instructions":[]}]'

    # recipe_json_format=

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    def payload(request):
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": request
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            # "temperature": 0.2,
            "max_tokens": 3000
        }
        return payload


    requests_list=[recipe_request_1,recipe_request_2,recipe_request_3,recipe_request_4]

    for index, request in enumerate(requests_list,start=1):
        print('index: ' + str(index))
        print('length ' + str(len(requests_list)))
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload(request))
        response_data = response.json()
        # print(request)
        print(response_data)
        
        parsed_data=response_data['choices'][0]['message']['content']
        # formatted_data = parsed_data.replace('```json\n', '').replace('```', '').strip()
        formatted_data = re.sub(r'^```json\n|\n```$', '', parsed_data, flags=re.MULTILINE).strip()
        # print(type(formatted_data))
        try:
            parsed_list = json.loads(formatted_data)
        except json.JSONDecodeError:
        # Handle the error when the data is not valid JSON
            print('json decode error')
            parsed_list = "not a fridge"
            if index < (len(requests_list)):
                continue
            os.remove(resized_image_path)
            return parsed_list
        except Exception as e:
        # Handle other unforeseen errors
            print(f"An error occurred: {e}")
            parsed_list = "not a fridge"
            if index < (len(requests_list)):
                continue
            os.remove(resized_image_path)
            return parsed_list
        break
        # print(parsed_list[1])

    
    if generate_with_image:
        title_list=[]
        for recipe in parsed_list:
            # print(recipe['title'])
            title_list.append(recipe['title'])
        # print(title_list)
        image_urls=generate_images(title_list)
        for recipe, url in zip(parsed_list, image_urls):
            recipe['image_url'] = url
        # print(parsed_list)

        if 'usage' in response_data:
            tokens_used = response_data['usage'].get('total_tokens', 'Unknown')
            print(f"Tokens used: {tokens_used}")
        else:
            print("Token usage information is not available in the response.")


        os.remove(resized_image_path)
        print(f"Resized image at {resized_image_path} has been deleted.")
        print(parsed_list)

        return(parsed_list)


    if generate_with_image == False:
        if 'usage' in response_data:
            tokens_used = response_data['usage'].get('total_tokens', 'Unknown')
            print(f"Tokens used: {tokens_used}")
        else:
            print("Token usage information is not available in the response.")


        os.remove(resized_image_path)
        print(f"Resized image at {resized_image_path} has been deleted.")

        print(parsed_list)
        return parsed_list

