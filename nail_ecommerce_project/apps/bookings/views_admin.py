from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect

from .models import Booking, BookingStatus
from logs.logger import get_logger

logger = get_logger(__name__)


class AdminBookingListView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'bookings/admin_booking_list.html'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        status_filter = request.GET.get('status')
        search_query = request.GET.get('q', '')
        page_number = request.GET.get('page')

        bookings = Booking.objects.select_related('customer', 'service')

        if status_filter:
            bookings = bookings.filter(status=status_filter)

        if search_query:
            bookings = bookings.filter(
                Q(service__title__icontains=search_query) |
                Q(customer__full_name__icontains=search_query)
            )

        paginator = Paginator(bookings, 10)
        page_obj = paginator.get_page(page_number)

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'bookings': page_obj.object_list,
            'status_choices': BookingStatus.choices,
            'current_filter': status_filter,
            'search_query': search_query,
            'terminal_statuses': ['COMPLETED_SERVICE', 'CANCELLED_SERVICE'],
        })


class UpdateBookingStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        new_status = request.POST.get('status')

        if new_status not in dict(BookingStatus.choices):
            messages.error(request, "Invalid status.")
            return redirect('bookings_admin:bookings_list')

        if booking.status == new_status:
            messages.info(request,
                          f"No change: Booking #{booking.id} already has status '{booking.get_status_display()}'.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        booking.status = new_status
        booking.save()
        messages.success(request, f"Booking #{booking.id} status updated to {booking.get_status_display()}")
        return redirect('bookings_admin:bookings_list')
