from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from .models import Booking
from .serializers import BookingSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.dateparse import parse_date
from .models import TIME_SLOT_CHOICES


class BookingListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(customer=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


class BookingDetailAPIView(generics.RetrieveAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(customer=self.request.user)



class BookingStatusUpdateAPIView(generics.UpdateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Booking.objects.all()
    http_method_names = ['patch', 'put']


class BookingCancelAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.status == 'CANCELLED_SERVICE':
            return Response({"detail": "Booking already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'CANCELLED_SERVICE'
        booking.save()
        return Response({"detail": "Booking cancelled successfully."}, status=status.HTTP_200_OK)


#Additional Views
class AdminBookingUpdateAPIView(generics.UpdateAPIView):
    serializer_class = BookingSerializer
    queryset = Booking.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Booking.objects.all()


class AvailableSlotsAPIView(APIView):
    permission_classes = [permissions.AllowAny]  # Or IsAuthenticated if required

    def get(self, request, *args, **kwargs):
        from .models import Booking

        service_id = request.GET.get("service")
        date_str = request.GET.get("date")
        if not service_id or not date_str:
            return Response({"error": "Missing parameters"}, status=400)

        date = parse_date(date_str)
        booked_slots = Booking.objects.filter(service_id=service_id, date=date).values_list('time_slot', flat=True)
        available_slots = [slot for slot, _ in TIME_SLOT_CHOICES if slot not in booked_slots]

        return Response({"available_slots": available_slots})
