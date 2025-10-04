from django.urls import path
from .views_cart import CartCheckoutView, CartDetailView, AddToCartView, RemoveFromCartView
from .views_buy_now import BuyNowView, BuyNowCheckoutView
from .views_payment import OrderSuccessView, OrderFailedView, CartPaymentVerifyView, \
    BuyNowPaymentVerifyView, CartCallbackView, BuyNowCallbackView
from .views_orders import CustomerOrderListView, UserCancelOrderView

app_name = 'orders'

urlpatterns = [
    path('buy-now/', BuyNowView.as_view(), name='buy_now'),
    path('checkout-buy-now/', BuyNowCheckoutView.as_view(), name='checkout_buy_now'),
    path('cart/', CartDetailView.as_view(), name='cart_detail'),
    path('checkout-cart/', CartCheckoutView.as_view(), name='checkout_cart'),
    path('cart/remove/<int:variant_id>/', RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('cart/callback/', CartCallbackView.as_view(), name='cart_callback'),
    path('buy-now/callback/', BuyNowCallbackView.as_view(), name='buy_now_callback'),
    path('success/<int:order_id>/', OrderSuccessView.as_view(), name='order_success'),
    path('failed/', OrderFailedView.as_view(), name='order_failed'),
    path('my-orders/', CustomerOrderListView.as_view(), name='order_list'),
    path('cart/add/', AddToCartView.as_view(), name='add_to_cart'),
    path('verify-cart-payment/', CartPaymentVerifyView.as_view(), name='verify_cart_payment'),
    path('verify-buy-now-payment/', BuyNowPaymentVerifyView.as_view(), name='verify_buy_now_payment'),
    path('my-orders/<int:pk>/cancel/', UserCancelOrderView.as_view(), name='user_cancel_order'),

]
