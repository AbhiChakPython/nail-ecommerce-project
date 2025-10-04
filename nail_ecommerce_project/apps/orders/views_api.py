from rest_framework import generics, permissions
from .models import Order
from .serializers import OrderSerializer


class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission: Allow admin to access all orders,
    and customers only their own orders.
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user == request.user


class OrderCreateAPIView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()


class OrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=user)


class OrderDetailAPIView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]
    queryset = Order.objects.all()
