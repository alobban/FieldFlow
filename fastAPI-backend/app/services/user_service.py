"""
User service for user-related business logic.
"""

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserStatus
from app.models.role import ROLE_TENANT_ADMIN, ROLE_TENANT_USER
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import (
    UserNotFoundException,
    DuplicateException,
    ValidationException,
)
from app.core.security import (
    hash_password,
    verify_password,
    generate_username,
)


class UserService:
    """
    Service for user business operations.
    
    Handles user creation, authentication, and management
    within tenant context.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize service with database session.
        
        Args:
            session: Async database session
        """
        self.session = session
        self.user_repository = UserRepository(session)
        self.role_repository = RoleRepository(session)
    
    async def get_by_id(self, user_id: UUID) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User UUID
        
        Returns:
            User instance
        
        Raises:
            UserNotFoundException: If user not found
        """
        user = await self.user_repository.get_with_roles(user_id)
        
        if not user:
            raise UserNotFoundException(identifier=str(user_id))
        
        return user
    
    async def get_by_username(
        self,
        username: str,
        tenant_id: UUID,
    ) -> User:
        """
        Get user by username within tenant.
        
        Args:
            username: Username
            tenant_id: Tenant UUID
        
        Returns:
            User instance
        
        Raises:
            UserNotFoundException: If user not found
        """
        user = await self.user_repository.get_by_username(username, tenant_id)
        
        if not user:
            raise UserNotFoundException(identifier=username)
        
        return user
    
    async def get_by_email(
        self,
        email: str,
        tenant_id: UUID,
    ) -> User:
        """
        Get user by email within tenant.
        
        Args:
            email: Email address
            tenant_id: Tenant UUID
        
        Returns:
            User instance
        
        Raises:
            UserNotFoundException: If user not found
        """
        user = await self.user_repository.get_by_email(email, tenant_id)
        
        if not user:
            raise UserNotFoundException(identifier=email)
        
        return user
    
    async def create(
        self,
        data: UserCreate,
        tenant_id: UUID,
        is_tenant_owner: bool = False,
        assign_admin_role: bool = False,
    ) -> tuple[User, bool]:
        """
        Create a new user.
        
        Args:
            data: User creation data
            tenant_id: Tenant UUID
            is_tenant_owner: Whether user is tenant owner
            assign_admin_role: Whether to assign admin role
        
        Returns:
            Tuple of (created user, username_was_generated)
        
        Raises:
            DuplicateException: If username or email exists
        """
        username_was_generated = False
        
        # Check for duplicate email
        if await self.user_repository.email_exists(data.email, tenant_id):
            raise DuplicateException(resource="User", field="email")
        
        # Handle username
        if data.username:
            # Check if provided username exists
            if await self.user_repository.username_exists(data.username, tenant_id):
                raise DuplicateException(resource="User", field="username")
            username = data.username.lower()
        else:
            # Generate username
            base_username = self._generate_base_username(
                data.first_name,
                data.last_name,
            )
            username = await self.user_repository.generate_unique_username(
                base_username,
                tenant_id,
            )
            username_was_generated = True
        
        # Create user
        user_data = {
            "tenant_id": tenant_id,
            "username": username,
            "email": data.email.lower(),
            "password_hash": hash_password(data.password),
            "first_name": data.first_name,
            "last_name": data.last_name,
            "status": UserStatus.PENDING,
            "is_active": True,
            "is_tenant_owner": is_tenant_owner,
            "email_verified": False,
        }
        
        user = await self.user_repository.create(user_data)
        
        # Assign role
        role_name = ROLE_TENANT_ADMIN if assign_admin_role else ROLE_TENANT_USER
        await self._assign_role(user.id, role_name, is_primary=True)
        
        # Refresh to get roles
        user = await self.user_repository.get_with_roles(user.id)
        
        return user, username_was_generated
    
    async def create_tenant_owner(
        self,
        data: UserCreate,
        tenant_id: UUID,
    ) -> tuple[User, bool]:
        """
        Create a tenant owner user with admin role.
        
        Args:
            data: User creation data
            tenant_id: Tenant UUID
        
        Returns:
            Tuple of (created user, username_was_generated)
        """
        return await self.create(
            data=data,
            tenant_id=tenant_id,
            is_tenant_owner=True,
            assign_admin_role=True,
        )
    
    async def update(
        self,
        user_id: UUID,
        data: UserUpdate,
    ) -> User:
        """
        Update a user.
        
        Args:
            user_id: User UUID
            data: Update data
        
        Returns:
            Updated user
        
        Raises:
            UserNotFoundException: If user not found
            DuplicateException: If email exists
        """
        # Get current user
        user = await self.get_by_id(user_id)
        
        # Check for duplicate email if being changed
        if data.email and data.email.lower() != user.email.lower():
            if await self.user_repository.email_exists(
                data.email,
                user.tenant_id,
                exclude_id=user_id,
            ):
                raise DuplicateException(resource="User", field="email")
        
        # Update user
        update_dict = data.model_dump(exclude_unset=True)
        if "email" in update_dict:
            update_dict["email"] = update_dict["email"].lower()
        
        updated_user = await self.user_repository.update(user_id, update_dict)
        
        if not updated_user:
            raise UserNotFoundException(identifier=str(user_id))
        
        return await self.user_repository.get_with_roles(user_id)
    
    async def delete(self, user_id: UUID) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: User UUID
        
        Returns:
            True if deleted
        
        Raises:
            UserNotFoundException: If user not found
            ValidationException: If user is tenant owner
        """
        user = await self.get_by_id(user_id)
        
        if user.is_tenant_owner:
            raise ValidationException(
                "Cannot delete tenant owner. Transfer ownership first."
            )
        
        return await self.user_repository.delete(user_id)
    
    async def authenticate(
        self,
        username_or_email: str,
        password: str,
        tenant_id: UUID,
    ) -> User | None:
        """
        Authenticate a user.
        
        Args:
            username_or_email: Username or email
            password: Password to verify
            tenant_id: Tenant UUID
        
        Returns:
            User if authentication successful, None otherwise
        """
        # Try to find user by email first, then username
        user = await self.user_repository.get_by_email(
            username_or_email,
            tenant_id,
        )
        
        if not user:
            user = await self.user_repository.get_by_username(
                username_or_email,
                tenant_id,
            )
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    async def get_tenant_users(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> List[User]:
        """
        Get all users for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            skip: Records to skip
            limit: Maximum records
            include_inactive: Include inactive users
        
        Returns:
            List of users
        """
        return await self.user_repository.get_tenant_users(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            include_inactive=include_inactive,
        )
    
    async def search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 10,
    ) -> List[User]:
        """
        Search users within a tenant.
        
        Args:
            tenant_id: Tenant UUID
            query: Search string
            limit: Maximum results
        
        Returns:
            List of matching users
        """
        return await self.user_repository.search_users(
            tenant_id=tenant_id,
            query_string=query,
            limit=limit,
        )
    
    async def validate_username(
        self,
        username: str,
        tenant_id: UUID,
        exclude_id: UUID | None = None,
    ) -> dict:
        """
        Validate a username.
        
        Args:
            username: Username to validate
            tenant_id: Tenant UUID
            exclude_id: User ID to exclude from check
        
        Returns:
            Validation result dict
        """
        import re
        
        validation_errors = []
        
        # Check length
        if len(username) < 3:
            validation_errors.append("Username must be at least 3 characters")
        if len(username) > 50:
            validation_errors.append("Username must be at most 50 characters")
        
        # Check format
        username_pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
        if not re.match(username_pattern, username):
            validation_errors.append(
                "Username must start with a letter and contain only "
                "letters, numbers, and underscores"
            )
        
        is_valid_format = len(validation_errors) == 0
        
        # Check availability only if format is valid
        is_available = False
        if is_valid_format:
            is_available = not await self.user_repository.username_exists(
                username.lower(),
                tenant_id,
                exclude_id=exclude_id,
            )
        
        # Generate message
        if not is_valid_format:
            message = "; ".join(validation_errors)
        elif is_available:
            message = "Username is available"
        else:
            message = "Username is already taken"
        
        return {
            "username": username,
            "is_available": is_available,
            "is_valid_format": is_valid_format,
            "message": message,
            "validation_errors": validation_errors,
        }
    
    async def generate_username_suggestions(
        self,
        first_name: str | None,
        last_name: str | None,
        tenant_id: UUID,
        count: int = 3,
    ) -> List[str]:
        """
        Generate username suggestions.
        
        Args:
            first_name: Optional first name
            last_name: Optional last name
            tenant_id: Tenant UUID
            count: Number of suggestions
        
        Returns:
            List of available username suggestions
        """
        suggestions = []
        
        if first_name or last_name:
            # Generate name-based suggestions
            base_options = self._generate_username_options(first_name, last_name)
            
            for base in base_options:
                if len(suggestions) >= count:
                    break
                
                username = await self.user_repository.generate_unique_username(
                    base,
                    tenant_id,
                )
                if username not in suggestions:
                    suggestions.append(username)
        
        # Fill remaining with random usernames
        while len(suggestions) < count:
            username = generate_username(tenant_id=str(tenant_id))
            if not await self.user_repository.username_exists(username, tenant_id):
                if username not in suggestions:
                    suggestions.append(username)
        
        return suggestions[:count]
    
    async def verify_email(self, user_id: UUID) -> User:
        """
        Mark user's email as verified.
        
        Args:
            user_id: User UUID
        
        Returns:
            Updated user
        """
        user = await self.user_repository.verify_email(user_id)
        
        if not user:
            raise UserNotFoundException(identifier=str(user_id))
        
        return user
    
    async def deactivate(self, user_id: UUID) -> User:
        """
        Deactivate a user.
        
        Args:
            user_id: User UUID
        
        Returns:
            Deactivated user
        """
        user = await self.get_by_id(user_id)
        
        if user.is_tenant_owner:
            raise ValidationException(
                "Cannot deactivate tenant owner. Transfer ownership first."
            )