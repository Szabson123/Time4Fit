from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from faker import Faker
from .models import ApplicationUser
import time
from PIL import Image, ImageDraw

class BulkCreateUsersView(APIView):
    def post(self, request, *args, **kwargs):
        fake = Faker(['pl_PL'])
        total_records = 100_000
        batch_size = 5000
        
        users_pool = []
        
        for _ in range(total_records):
            user = ApplicationUser(
                name=fake.first_name(),
                surname=fake.last_name(),
                email=fake.unique.email(),
                phone=fake.phone_number(),
                is_valid=fake.boolean(chance_of_getting_true=50)
            )
            users_pool.append(user)
        
        ApplicationUser.objects.bulk_create(users_pool, batch_size=batch_size, ignore_conflicts=True)
        
        return Response(
            {"message": f"Successfully triggered creation of {total_records} users."}, 
            status=status.HTTP_201_CREATED
        )
    



class SynchronousReportView(APIView):
    """
    Widok realizujący synchroniczne, blokujące generowanie raportu.
    """
    def post(self, request):
        user_id = request.data.get('user_id', 1)
        
        image = Image.new("RGB", (1500, 1500), color="white")
        draw = ImageDraw.Draw(image)
        for i in range(7500):  # Pętla generująca obciążenie rdzenia procesora
            draw.text((10, 10), f"Raport ID: {user_id} - Iteracja: {i}", fill="black")
            
        # 2. Sekcja I/O-bound: Symulacja zapisu dyskowego i opóźnienia sieciowego zewnętrznego API
        # Zgodnie z metodologią badawczą opóźnienie wynosi 400 ms
        time.sleep(0.4)
        
        return Response(
            {"status": "Sukces", "message": "Raport wygenerowany i zapisany synchronicznie."}, 
            status=status.HTTP_200_OK
        )