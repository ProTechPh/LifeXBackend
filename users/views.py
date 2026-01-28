from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdmin

User = get_user_model()

@extend_schema_view(
    get=extend_schema(
        tags=['User Management'],
        summary='Get user details',
        description='Retrieve details of a specific user (Admin only)',
    ),
    put=extend_schema(
        tags=['User Management'],
        summary='Update user',
        description='Update user information (Admin only)',
    ),
    patch=extend_schema(
        tags=['User Management'],
        summary='Partially update user',
        description='Partially update user information (Admin only)',
    ),
    delete=extend_schema(
        tags=['User Management'],
        summary='Delete user',
        description='Delete a user account (Admin only)',
    ),
)
class UserAdminView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin can view, update or delete any user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'pk'


@extend_schema(
    tags=['Authentication'],
    summary='Register new user',
    description='Register a new user account. Only PATIENT role is allowed for self-registration. Staff accounts must be created by administrators.',
    examples=[
        OpenApiExample(
            'Patient Registration',
            value={
                'email': 'patient@example.com',
                'password': 'securepassword123',
                'password2': 'securepassword123',
                'first_name': 'John',
                'last_name': 'Doe',
                'role': 'PATIENT'
            }
        )
    ]
)
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST'), name='dispatch')
class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user account
    Rate limited to 5 registrations per minute per IP
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Authentication'],
    summary='User login',
    description='Authenticate user and return JWT tokens. Supports both email and username authentication.',
    examples=[
        OpenApiExample(
            'Login Example',
            value={
                'email': 'user@example.com',
                'password': 'password123'
            }
        )
    ]
)
@method_decorator(ratelimit(key='ip', rate='10/m', method='POST'), name='dispatch')
class UserLoginView(APIView):
    """
    Login user and return JWT tokens
    Rate limited to 10 login attempts per minute per IP
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email'].lower().strip()
        password = serializer.validated_data['password'].strip()
        
        user = authenticate(email=email, password=password)
        
        if user is None:
            user = authenticate(username=email, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    summary='User logout',
    description='Logout user by blacklisting the refresh token',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'refresh_token': {
                    'type': 'string',
                    'description': 'JWT refresh token to blacklist'
                }
            },
            'required': ['refresh_token']
        }
    }
)
class UserLogoutView(APIView):
    """
    Logout user by blacklisting the refresh token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Invalid token or token already blacklisted'},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema_view(
    get=extend_schema(
        tags=['User Management'],
        summary='Get user profile',
        description='Get the authenticated user\'s profile information',
    ),
    put=extend_schema(
        tags=['User Management'],
        summary='Update user profile',
        description='Update the authenticated user\'s profile information',
    ),
    patch=extend_schema(
        tags=['User Management'],
        summary='Partially update user profile',
        description='Partially update the authenticated user\'s profile information',
    ),
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer


@extend_schema(
    tags=['Authentication'],
    summary='Change password',
    description='Change the authenticated user\'s password',
    examples=[
        OpenApiExample(
            'Change Password',
            value={
                'old_password': 'currentpassword',
                'new_password': 'newpassword123',
                'new_password2': 'newpassword123'
            }
        )
    ]
)
class ChangePasswordView(APIView):
    """
    Change user password
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Set new password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['User Management'],
    summary='List users',
    description='List users based on role permissions. Admins see all users, medical staff see patients, patients see only themselves.',
    parameters=[
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search users by name or email'
        ),
    ]
)
class UserListView(generics.ListAPIView):
    """
    List all users (Admin and Staff only)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Admins can see all users
        if user.role == 'ADMIN':
            return User.objects.all()
        
        # Medical Staff (Receptionist, Nurse, Doctor) can see Patients
        if user.role in ['RECEPTIONIST', 'NURSE', 'DOCTOR']:
            return User.objects.filter(role='PATIENT')
        
        # Patients can only see themselves
        return User.objects.filter(id=user.id)