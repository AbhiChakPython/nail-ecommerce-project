from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from .forms import ProductForm, ProductVariantFormSet
from django.db.models import Q
from .models import Product, ProductCategory, ProductGalleryImage
from .forms import ProductGalleryImageForm
from logs.logger import get_logger
logger = get_logger(__name__)


class IsAdminMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Only admin staff can access this view.")
        return super().dispatch(request, *args, **kwargs)


class IsCustomerMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You must be logged in to view this page.")
            return redirect(reverse('users:login'))  # 🔁 redirect to login

        if not getattr(request.user, 'is_customer', False):
            messages.error(request, "Only customers can access this section.")
            return redirect('users:profile')  # or homepage or another fallback

        return super().dispatch(request, *args, **kwargs)


class IsSuperUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path())
        raise PermissionDenied("You do not have permission to perform this action.")


class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 8

    def get_queryset(self):
        queryset = Product.objects.filter(is_available=True).order_by('-created_at')
        q = self.request.GET.get('q')
        category_slug = self.request.GET.get('category')

        if q:
            logger.info(f"Product search query: '{q}'")
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )

        if category_slug and category_slug != "None":
            logger.info(f"Filtering products by category: '{category_slug}'")
            queryset = queryset.filter(categories__slug=category_slug)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = context['products']

        for product in products:
            variants = product.variants.all()
            if variants.exists():
                # Use the lowest variant price as base price for discount calculation
                base_price = variants.order_by('price').first().price
                product.discounted_price = product.get_discounted_price(base_price)
            else:
                product.discounted_price = None  # No variants, no price

        context['categories'] = ProductCategory.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['q'] = self.request.GET.get('q', '')

        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['added'] = self.request.GET.get('added', '')
        product = context['product']
        variants = product.variants.all()
        context['variants'] = variants

        if variants.exists():
            # Calculate product discounted price based on lowest variant price
            base_price = variants.order_by('price').first().price
            context['discounted_price'] = product.get_discounted_price(base_price)
        else:
            context['discounted_price'] = None

        # Assign discounted price to each variant using its own method
        for variant in variants:
            variant.discounted_price = variant.get_discounted_price()

        return context


class ProductCreateView(IsSuperUserRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_create.html'
    success_url = reverse_lazy('products:product_list')

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        formset = ProductVariantFormSet(instance=Product())  # 🟢 Important fix
        return render(request, self.template_name, {'form': form, 'formset': formset})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        print("🟨 POST keys:", list(request.POST.keys()))
        if form.is_valid():
            product = form.save()
            formset = ProductVariantFormSet(request.POST, request.FILES, instance=product)
            print("🟥 Formset valid:", formset.is_valid())
            print("🟥 Formset errors:", formset.errors)
            print("🟥 Formset non-form errors:", formset.non_form_errors())
            if formset.is_valid():
                logger.info(f"New product created: {product.name} by {request.user}")
                formset.save()
                messages.success(request, "Product added successfully.")
                return redirect('products:product_detail', slug=product.slug)
        else:
            logger.warning("Product creation form is invalid.")
            formset = ProductVariantFormSet(request.POST, request.FILES)

        return render(request, self.template_name, {'form': form, 'formset': formset})

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except IntegrityError as e:
            logger.error(f"Product creation failed due to integrity error: {str(e)}")
            messages.error(self.request,
                           "A product with a similar name already exists. Please choose a different name.")
            return self.form_invalid(form)


class ProductUpdateView(IsSuperUserRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_update.html'
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save()
        form.save_m2m()
        messages.success(self.request, "Product updated successfully.")
        logger.info(f"Product updated: {self.object.name} by {self.request.user}")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        logger.warning(f"Product update failed by {self.request.user}. Errors: {form.errors}")
        return super().form_invalid(form)


class ProductVariantManageView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'products/manage_variants.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        formset = ProductVariantFormSet(instance=product)
        return render(request, self.template_name, {
            'product': product,
            'formset': formset
        })

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        formset = ProductVariantFormSet(request.POST, instance=product)

        # ✅ DEBUGGING START
        print("🧪 Formset prefix used:", formset.prefix)
        print("🧪 POST contains keys:", list(request.POST.keys()))
        print("🧪 ManagementForm.is_valid():", formset.management_form.is_valid())
        print("🧪 ManagementForm errors:", formset.management_form.errors)
        # ✅ DEBUGGING END

        if formset.is_valid():
            print("✅ Formset is valid. Proceeding to save.")
            saved_instances = formset.save()
            print("✅ Saved instances:", saved_instances)

            messages.success(request, "Variants updated successfully.")
            logger.info(f"Variants updated for product '{product.name}' by {request.user}")
            print("✅ Redirecting after successful save")
            return redirect('products:product_detail', slug=product.slug)

        print("❌ Formset is NOT valid. Errors:", formset.errors)
        messages.error(request, "Please correct the errors below.")
        return render(request, self.template_name, {
            'product': product,
            'formset': formset
        })

class ProductDeleteView(IsSuperUserRequiredMixin, DeleteView):
    model = Product
    template_name = 'products/product_confirm_delete.html'
    success_url = reverse_lazy('products:product_list')

    def post(self, request, *args, **kwargs):
        product = self.get_object()
        logger.info(f"Product deleted: {product.name} by {request.user}")
        messages.success(self.request, "Product deleted successfully.")
        return super().post(request, *args, **kwargs)

class ManageProductGalleryView(IsSuperUserRequiredMixin, View):
    template_name = 'products/manage_gallery.html'

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        form = ProductGalleryImageForm()
        return render(request, self.template_name, {
            'product': product,
            'form': form,
            'gallery': product.gallery_images.all()
        })

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        form = ProductGalleryImageForm(request.POST, request.FILES)

        print("Files:", request.FILES)
        print("DEBUG >> Form received:", form)

        if form.is_valid():
            print("Form cleaned data:", form.cleaned_data)
            print("DEBUG >> is_valid: True")
            print("DEBUG >> errors:", form.errors)

            image = form.save(commit=False)
            image.product = product
            image.save()
            logger.info(f"Gallery image added for product: {product.name} by {request.user}")
            messages.success(request, "Gallery image added.")
            return redirect('products:manage_gallery', slug=product.slug)
        else:
            print("DEBUG >> is_valid: False")
            print("DEBUG >> errors:", form.errors)
            logger.warning(f"Gallery image form invalid for product: {product.name}")

        return render(request, self.template_name, {
            'product': product,
            'form': form,
            'gallery': product.gallery_images.all()
        })

class DeleteGalleryImageView(IsSuperUserRequiredMixin, View):
    @method_decorator(require_POST)
    def post(self, request, pk):
        image = get_object_or_404(ProductGalleryImage, pk=pk)
        product_slug = image.product.slug
        image.delete()
        logger.info(f"Gallery image deleted (ID: {pk}) by {request.user}")
        messages.success(request, "Image deleted from gallery.")
        return redirect('products:manage_gallery', slug=product_slug)

