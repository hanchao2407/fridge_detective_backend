from PIL import Image
import base64
import requests
import os
from dotenv import load_dotenv
import json
import time
from concurrent.futures import ThreadPoolExecutor  # Import ThreadPoolExecutor
from openai import OpenAI



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
            model="dall-e-2",
            prompt=prompt,
            size="256x256",
            quality="standard",
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

def generate_recipe_from_image(image_path,recipe_amount,generate_with_image):
    # print(image_path)
    resized_image_path = resize_image(image_path)
    base64_image = encode_image(resized_image_path)

    recipe_request = 'generate ' + recipe_amount +'recipe based on ingredients on the picture'
    recipe_custom_function = [
        {
            'name': 'generate_recipe',
            'description': 'generate a recipe and put in json format ',
            'parameters': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': 'Name of the dish'
                    },
                    'shortdescription': {
                        'type': 'string',
                        'description': 'Short description of the recipe.'
                    },
                    'preptime': {
                        'type': 'int',
                        'description': 'the preparation time'
                    },
                    'ingredients': {
                        'type': 'list',
                        'description': '[[ingredient, amount as string]]'
                    },
                    'instructions': {
                        'type': 'list',
                        'description': 'instruction step by step '
                    }
                    
                }
            }
        }
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": recipe_request
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
        "functions" : recipe_custom_function,
        "function_call" : 'auto',
        "max_tokens": 3000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    response_data = response.json()
    print(response_data)
    
    parsed_data=response_data['choices'][0]['message']['content']
    formatted_data = parsed_data.replace('```json\n', '').replace('```', '').strip()
    # print(type(formatted_data))
    try:
        parsed_list = json.loads(formatted_data)
    except json.JSONDecodeError:
    # Handle the error when the data is not valid JSON
        print('json decode error')
        parsed_list = "not a fridge"
        os.remove(resized_image_path)
        return parsed_list
    except Exception as e:
    # Handle other unforeseen errors
        print(f"An error occurred: {e}")
        parsed_list = "not a fridge"
        os.remove(resized_image_path)
        return parsed_list
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

