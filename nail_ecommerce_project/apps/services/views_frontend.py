from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q
from .form import ServiceForm, ServiceGalleryImageForm
from .models import Service
from logs.logger import get_logger
logger = get_logger(__name__)


class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


# Admin Create View
class ServiceCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'services/service_form.html'
    success_url = reverse_lazy('services:service_list')

    def form_valid(self, form):
        try:
            logger.info(f"Service created by user: {self.request.user.username}")
            return super().form_valid(form)
        except IntegrityError:
            logger.warning("Service creation failed due to IntegrityError: Duplicate slug")
            messages.error(self.request, "Slug already exists. Please enter a unique one.")
            return self.form_invalid(form)


class ServiceUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'services/service_form.html'
    success_url = reverse_lazy('services:service_list')

    def form_valid(self, form):
        logger.info(f"Service updated by user: {self.request.user.username}")
        return super().form_valid(form)


class ServiceDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Service
    template_name = 'services/service_confirm_delete.html'
    success_url = reverse_lazy('services:service_list')

    def delete(self, request, *args, **kwargs):
        logger.info(f"Service deleted by user: {request.user.username}")
        return super().delete(request, *args, **kwargs)


class ServiceListView(ListView):
    model = Service
    template_name = 'services/service_list.html'
    context_object_name = 'services'
    paginate_by = 6

    def get_queryset(self):
        queryset = Service.objects.filter(is_active=True).order_by('-created_at')
        logger.debug("Service list view accessed")

        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(short_description__icontains=q)
            )
            logger.info(f"Service search performed with query: '{q}'")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context

class ServiceDetailView(DetailView):
    model = Service
    template_name = 'services/service_detail.html'
    context_object_name = 'service'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'


class ManageServiceGalleryView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, slug):
        service = get_object_or_404(Service, slug=slug)
        form = ServiceGalleryImageForm()
        gallery_images = service.gallery_images.all()
        logger.info(f"Gallery management accessed for service: {slug} by {request.user.username}")
        return render(request, 'services/service_manage_gallery.html', {
            'service': service,
            'form': form,
            'gallery_images': gallery_images,
        })

    def post(self, request, slug):
        service = get_object_or_404(Service, slug=slug)
        form = ServiceGalleryImageForm(request.POST, request.FILES)
        if form.is_valid():
            gallery_image = form.save(commit=False)
            gallery_image.service = service
            gallery_image.save()
            logger.info(f"Gallery image uploaded for service: {slug} by {request.user.username}")
            return redirect('services:service_manage_gallery', slug=service.slug)
        else:
            logger.warning(f"Invalid gallery form submission for service: {slug}")
        gallery_images = service.gallery_images.all()
        return render(request, 'services/service_manage_gallery.html', {
            'service': service,
            'form': form,
            'gallery_images': gallery_images,
        })



