from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import ListView, DetailView, UpdateView, TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from .models import TIME_SLOT_CHOICES
import razorpay
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from decimal import Decimal
from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from nail_ecommerce_project.apps.bookings.forms import BookingForm
from nail_ecommerce_project.apps.bookings.models import Booking
from nail_ecommerce_project.apps.services.models import Service
from .utils import send_booking_placed_email, send_booking_confirmed_email, calculate_booking_price
from ..products.views_frontend import IsCustomerMixin
from logs.logger import get_logger
logger = get_logger(__name__)

# Initialize once
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

class CustomerOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        allowed = user.is_authenticated and getattr(user, 'is_customer', False)
        if not allowed:
            logger.warning(f"Unauthorized access to customer-only view by {user}")
        return allowed

class BookingCreateView(LoginRequiredMixin, CustomerOnlyMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = 'bookings/booking_form.html'
    success_url = reverse_lazy('booking_list_create')
    login_url = settings.LOGIN_URL

    def get_initial(self):
        initial = super().get_initial()
        service_id = self.request.GET.get('service')
        if service_id:
            try:
                initial['service'] = Service.objects.get(pk=service_id)
                logger.debug(f"Pre-filled service ID: {service_id}")
            except Service.DoesNotExist:
                logger.warning(f"Service with ID {service_id} does not exist.")
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        logger.debug("Collecting context data for booking form rendering...")
        context = super().get_context_data(**kwargs)

        user = self.request.user
        has_address = hasattr(user, 'address') and user.address.is_complete
        context['has_address'] = has_address
        context['was_estimate'] = context.get('was_estimate', False)

        if has_address:
            addr = user.address
            full_address = f"{user.full_name}\n"
            if user.phone_number:
                full_address += f"Phone: {user.phone_number}\n"
            full_address += f"{addr.address_line1}, {addr.address_line2}, "
            if addr.landmark:
                full_address += f"Landmark: {addr.landmark}, "
            full_address += f"{addr.city}, {addr.state} - {addr.pincode}"
            context['full_address'] = full_address.strip()
        else:
            context['full_address'] = None

        return context

    def post(self, request, *args, **kwargs):
        self.object = None  # Required for CreateView context
        logger.info(f"POST received at BookingCreateView by user {request.user}")

        if request.POST.get('action') == 'estimate':
            logger.debug("Estimate action triggered")
            form = self.get_form()
            if not form.is_valid():
                logger.warning("Estimate form validation failed")
                return self.form_invalid(form)

            context = self.get_context_data(form=form)
            context['price_details'] = calculate_booking_price(
                service_id=form.cleaned_data['service'].id,
                number_of_customers=form.cleaned_data.get('number_of_customers', 1),
                is_home_service=form.cleaned_data.get('is_home_service', False)
            )
            context['was_estimate'] = True
            context['selected_date'] = form.cleaned_data.get('date')
            context['selected_slot'] = form.cleaned_data.get('time_slot')
            context['selected_service'] = form.cleaned_data.get('service')
            logger.info("Price estimation completed")
            return self.render_to_response(context)

        logger.debug("Final booking submission triggered")
        form = self.get_form()
        if not form.is_valid():
            logger.error("Final booking form submission failed validation")
            return self.form_invalid(form)

        booking = form.save(commit=False)
        booking.customer = request.user
        final_price = booking.get_final_price()
        logger.info(f"Validated booking form for user {request.user.username}, final price: ₹{final_price}")

        if booking.is_home_service:
            user = request.user
            booking.home_visit_fee = Decimal('250.00')
            try:
                address = user.address
                if not address.use_for_home_service:
                    logger.warning("Address exists but not allowed for home service")
                    form.add_error(None, "Your saved address is not marked for home service.")
                    return self.form_invalid(form)
                full_address = f"{address.address_line1}, {address.address_line2}, "
                if address.landmark:
                    full_address += f"Landmark: {address.landmark}, "
                full_address += f"{address.city}, {address.state} - {address.pincode}"
                booking.home_delivery_address = full_address
                logger.debug(f"Captured full home delivery address: {full_address}")
            except Exception as e:
                logger.exception("Exception occurred while fetching address for home service")
                form.add_error(None, "Valid address required for home visit.")
                return self.form_invalid(form)

        # Razorpay Order Creation
        try:
            payment = razorpay_client.order.create({
                'amount': int(final_price * 100),
                'currency': 'INR',
                'payment_capture': '1',
                'notes': {
                    'Customer Email': booking.customer.email,
                    'Discount Applied': 'Yes' if booking.number_of_customers >= 2 else 'No',
                }
            })
            booking.razorpay_order_id = payment['id']
            logger.info(f"Razorpay order created: {payment['id']}")
        except Exception as e:
            logger.exception("Error while creating Razorpay order")
            form.add_error(None, "Failed to initiate payment. Please try again.")
            return self.form_invalid(form)

        booking.save()
        logger.info(f"Booking saved with ID {booking.id}, Razorpay Order ID: {booking.razorpay_order_id}")
        return redirect('bookings:checkout', booking_id=booking.id)


class BookingCheckoutView(IsCustomerMixin, View):
    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

        context = {
            'booking': booking,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'show_payment_modal': not booking.razorpay_payment_id,  # 🔑 Razorpay not paid yet
        }
        return render(request, 'bookings/checkout.html', context)


class BookingSuccessView(IsCustomerMixin, TemplateView):
    template_name = 'bookings/success.html'

    def get(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(Booking, pk=booking_id, customer=request.user)
        logger.info(f"Booking payment successful for user {request.user.username}, booking ID {booking_id}")
        return self.render_to_response({'booking': booking})

class BookingFailedView(IsCustomerMixin, TemplateView):
    template_name = 'bookings/failed.html'

    def get(self, request, booking_id, *args, **kwargs):
        booking = get_object_or_404(Booking, pk=booking_id, customer=request.user)
        logger.warning(f"Booking payment failed for user {request.user.username}, booking ID {booking_id}")
        return self.render_to_response({'booking': booking})


@method_decorator(csrf_exempt, name='dispatch')
class BookingPaymentCallbackView(View):
    def post(self, request, booking_id, *args, **kwargs):
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            logger.error(f"Missing Razorpay data in callback for booking {booking_id}")
            return redirect('bookings:failed', booking_id=booking_id)

        try:
            booking = Booking.objects.get(pk=booking_id, razorpay_order_id=razorpay_order_id)
            params = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            razorpay_client.utility.verify_payment_signature(params)

            booking.is_paid = True
            booking.razorpay_payment_id = razorpay_payment_id
            booking.razorpay_signature = razorpay_signature
            booking.save()

            send_booking_placed_email(booking)  # Optional here
            logger.info(f"Payment verified and booking marked as paid: {booking_id}")
            return render(request, 'bookings/payment_processing.html', {'booking': booking})

        except razorpay.errors.SignatureVerificationError:
            booking = Booking.objects.filter(pk=booking_id).first()
            if booking:
                booking.is_paid = False
                booking.save()
            logger.warning(f"Signature verification failed for booking ID: {booking_id}")
            return redirect('bookings:failed', booking_id=booking_id)

        except Booking.DoesNotExist:
            logger.error(f"Booking not found during payment callback. ID={booking_id}")
            return redirect('bookings:failed', booking_id=booking_id)


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'bookings/booking_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        logger.info(f"Booking list accessed by user: {self.request.user.username}")
        return Booking.objects.filter(customer=self.request.user)


class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = 'bookings/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        logger.debug(f"Booking detail view accessed by {self.request.user.username}")
        return Booking.objects.filter(customer=self.request.user)


# Admin-only Booking Update (for status/staff update)
class BookingUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Booking
    fields = ['status', 'staff', 'notes']
    template_name = 'bookings/booking_update_form.html'
    success_url = reverse_lazy('bookings:booking_list_create')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def form_valid(self, form):
        original_status = self.get_object().status
        response = super().form_valid(form)
        new_status = form.instance.status

        if original_status != new_status and new_status == 'CONFIRMED_SERVICE':
            send_booking_confirmed_email(form.instance)

        logger.info(f"Booking updated by admin {self.request.user.username}")
        return response


class AvailableSlotsView(IsCustomerMixin, View):
    def get(self, request, *args, **kwargs):
        service_id = request.GET.get("service")
        date = request.GET.get("date")
        if not service_id or not date:
            logger.warning("AvailableSlotsView called with missing parameters")
            return JsonResponse({"error": "Missing parameters"}, status=400)

        booked_slots = Booking.objects.filter(service_id=service_id, date=date).values_list('time_slot', flat=True)
        available_slots = [slot for slot, _ in TIME_SLOT_CHOICES if slot not in booked_slots]

        logger.debug(f"Checking available slots for service={service_id}, date={date}")
        return JsonResponse({"available_slots": available_slots})

class BookingPriceEstimateView(IsCustomerMixin, View):
    def get(self, request):
        service_id = request.GET.get("service")
        num_customers = request.GET.get("number_of_customers", 1)
        home_service = request.GET.get("is_home_service") == "true"

        if not service_id:
            return JsonResponse({"error": "Missing service parameter"}, status=400)

        try:
            service = get_object_or_404(Service, pk=service_id)
            number_of_customers = int(num_customers)

            booking = Booking(
                service=service,
                number_of_customers=number_of_customers,
                is_home_service=home_service
            )
            breakdown = booking.get_price_breakdown()
            formatted = {
                'base_price': f"{breakdown['base_price']:.2f}",
                'regular_discount': f"{breakdown['regular_discount']:.2f}",
                'group_discount': f"{breakdown['group_discount']:.2f}",
                'home_visit_fee': f"{breakdown['home_visit_fee']:.2f}",
                'total_price': f"{breakdown['total_price']:.2f}"
            }

            logger.debug(f"Price breakdown estimate sent for user {request.user.username}: {formatted}")
            return JsonResponse({"breakdown": formatted})

        except Exception as e:
            logger.error(f"Error estimating booking price: {e}")
            return JsonResponse({"error": "Failed to calculate price"}, status=500)

class RetryBookingPaymentView(LoginRequiredMixin, View):
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

        # Already paid
        if booking.razorpay_payment_id:
            return redirect('bookings:checkout', booking_id=booking.id)

        # Recreate Razorpay order
        final_price = booking.get_final_price()
        try:
            payment = razorpay_client.order.create({
                'amount': int(final_price * 100),
                'currency': 'INR',
                'payment_capture': '1',
                'notes': {
                    'Booking ID': str(booking.id),
                    'Customer Email': booking.customer.email,
                }
            })
            booking.razorpay_order_id = payment['id']
            booking.save()
            logger.info(f"[RetryPayment] Razorpay order regenerated: {payment['id']} for booking {booking.id}")
        except Exception as e:
            logger.exception(f"[RetryPayment] Razorpay creation failed: {e}")
            # Redirect back with error message or handle as per your UI
            return redirect('bookings:checkout', booking_id=booking.id)

        return redirect('bookings:checkout', booking_id=booking.id)

class CancelBookingView(LoginRequiredMixin, View):
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

        if not booking.razorpay_payment_id:
            logger.info(f"[CancelBooking] Deleting unpaid booking ID {booking.id} by {request.user}")
            booking.delete()
        else:
            logger.warning(f"[CancelBooking] Attempt to cancel booking ID {booking.id} which already has a payment")

        return redirect('services:service_list')
