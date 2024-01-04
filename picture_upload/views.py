from django.shortcuts import render

# Create your views here.
# views.py in your Django app
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser, FormParser

import os
from django.conf import settings

import os
import uuid
from django.conf import settings
from rest_framework.decorators import api_view

from picture_upload.gpt_prompt import generate_recipe_from_image
import json
import time

API_KEY = '23f4gf34fmoi=p=[;32rf3' #for frontend authentification
def check_api_key(request):
    client_api_key = request.headers.get('X-API-KEY')
    print('key check')
    return client_api_key == API_KEY


@api_view(['POST'])
def upload_picture(request):
    if not check_api_key(request):
        return JsonResponse({'status': 'error', 'message': 'Invalid API Key'}, status=401)

    if 'picture' in request.FILES:
        picture = request.FILES['picture']
        recipe_amount = request.POST.get('recipe_amount')
        with_picture = request.POST.get('with_picture', 'false').lower() == 'true'  # Convert to boolean
        print(recipe_amount)
        print(with_picture)
        print(request.POST)
        print(type(with_picture))

        # Define a directory to save the image
        image_save_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_images')
        os.makedirs(image_save_path, exist_ok=True)

        # Generate a unique filename using UUID
        ext = picture.name.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{ext}"

        # Create a path for the image with the unique filename
        image_path = os.path.join(image_save_path, unique_filename)

        # Save the file
        with open(image_path, 'wb+') as destination:
            for chunk in picture.chunks():
                destination.write(chunk)

        # Print the image path
        # print(f"Image saved at: {image_path}")
        

        #gpt prompt comes here
        start_time = time.time()
        final_response = generate_recipe_from_image(image_path=image_path, recipe_amount=recipe_amount,generate_with_image=with_picture)
        end_time = time.time()
        duration = end_time - start_time
        print(f"Total response time: {duration} seconds")
        
        
        #Delete picture after usage
        os.remove(image_path)
        print(f"Image at {image_path} has been deleted.")


        return JsonResponse({
            'status': 'success',
            'message': 'Picture uploaded successfully',
            'image_path': image_path,
            'recipe': final_response  # Include the OpenAI API response here
        })

    else:
        return JsonResponse({'status': 'error', 'message': 'No picture uploaded'}, status=400)
