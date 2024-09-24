"""
Test for models
"""



from django.test import TestCase
from decimal import Decimal
from core import models
from django.contrib.auth import get_user_model
from unittest.mock import patch



def create_user(email='test@email.com', password='testpass123'):
    """Helper function to create a user"""
    return get_user_model().objects.create_user(email=email, password=password)

class ModelTests(TestCase):

    def test_create_user_with_email_successful(self):
        """Test creating a user with email successful"""

        email = "test@email.com"
        password = 'testpass123'

        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    
    def test_create_recipe(self):
        user= get_user_model().objects.create_user(
            'test@email.com',
            'testpass123',
        )
        recipe=models.Recipe.objects.create(
            user=user,
            title='Sample name recipe',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe'

        )
        self.assertEqual(str(recipe),recipe.title)

    def test_create_tag(self):
        user=create_user()
        tag=models.Tag.objects.create(user=user,name='Tag1')

        self.assertEqual(str(tag),tag.name)
    

    def test_create_ingredient(self):
        user=create_user()
        ingredient=models.Ingredient.objects.create(user=user,name='peproni')
        self.assertEqual(str(ingredient),ingredient.name)


    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test generating image path."""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')




    



