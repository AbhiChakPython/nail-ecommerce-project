from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from logs.logger import get_logger
logger = get_logger(__name__)


# User roles
class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    CUSTOMER = 'customer', 'Customer'

# Custom user manager
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            logger.error("Attempted to create user without username")
            raise ValueError("Users must have an username")
        email = self.normalize_email(email)

        role = extra_fields.get('role', UserRole.CUSTOMER)
        extra_fields.setdefault('role', role)

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        logger.info(f"User created via manager: {username} | Role: {role}")
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)

        if extra_fields.get('is_superuser') is not True:
            logger.error("Superuser creation failed: is_superuser not True")
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_staff') is not True:
            logger.error("Superuser creation failed: is_staff not True")
            raise ValueError('Superuser must have is_staff=True.')

        logger.info(f"Creating superuser: {username}")
        return self.create_user(username, email, password, **extra_fields)

# Custom user model
class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True, null=False, blank=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=10, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name', 'email']

    @property
    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.username

    def get_full_name(self):
        return self.full_name.strip() if self.full_name else self.username

    def save(self, *args, **kwargs):
        if self.pk:
            logger.debug(
                f"Updating user: {self.username} | Role: {self.role} | is_customer: {self.is_customer}")
        else:
            logger.info(f"Saving new user instance: {self.username} | Role: {self.role}")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.email})"


class CustomerAddress(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='address'
    )

    address_line1 = models.CharField(  # Flat, house no., building, etc.
        max_length=255,
        verbose_name="Flat or House No., Building, Apartment"
    )

    address_line2 = models.CharField(  # Area, Street, Sector, Village
        max_length=255,
        verbose_name="Area, Street, Sector, Village"
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Landmark (Optional)"
    )

    city = models.CharField(
        max_length=100,
        default='Pune',
        verbose_name="Town or City"
    )

    state = models.CharField(
        max_length=100,
        default='Maharashtra'
    )

    pincode = models.CharField(
        max_length=6,
        verbose_name="Pincode"
    )

    use_for_home_service = models.BooleanField(
        default=True,
        verbose_name="Use this address for home delivery or service"
    )

    @property
    def is_complete(self):
        required_fields = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.pincode,
        ]
        return all(bool(f and f.strip()) for f in required_fields)

    def __str__(self):
        return f"{self.user.username}'s address"

    class Meta:
        verbose_name = "Customer Address"
        verbose_name_plural = "Customer Addresses"
