from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
import tempfile
import os
from PIL import Image

from core.models import (
    Recipe,
    Tag,
    Ingredient
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return an image upload URL."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])



def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicRecipeAPITests(TestCase):

    def setUp(self):
        self.client=APIClient()


    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)



class PrivateRecipeApiTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123',
        )
        self.client.force_authenticate(self.user)
        


    def test_retrieve_recipes(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)


        res=self.client.get(RECIPES_URL)

        recipes=Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""
        other_user = get_user_model().objects.create_user(
            'other@example.com',
            'password123',
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    
    def test_get_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)



    def test_create_recipe(self):
        """Test creating a recipe."""
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'description': 'Sample description',
            'price': Decimal('5.99'),
        }
        res = self.client.post(RECIPES_URL, payload)
        print(f"Response status: {res.status_code}")
        print(f"Response data: {res.data}")  # Debugging step
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)




    def test_partial_update(self):
        """Test partial update of a recipe."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link,
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link='https://example.com/recipe.pdf',
            description='Sample recipe description.',
        )

        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com/new-recipe.pdf',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            print(f"Checking {k}: {getattr(recipe, k)} == {v}")  # Debugging step
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)


    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'description': 'New recipe description',
            'link': 'https://example.com/new-recipe.pdf',
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'description': 'New recipe description',
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_recipe_update_tag(self):
        recipe=create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Lunch'}]}
        url=detail_url(recipe.id)
        res=self.client.patch(url,payload,format='json')
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())


    def test_update_recipe_assign_tag(self):
        tag_breakfast=Tag.objects.create(user=self.user,name='break')
        recipe=create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)
        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url=detail_url(recipe.id)
        res=self.client.patch(url,payload,format='json')
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        self.assertIn(tag_lunch,recipe.tags.all())
        self.assertNotIn(tag_breakfast,recipe.tags.all())

    def test_clear_recipe_tags(self):
        tag_breakfast=Tag.objects.create(user=self.user,name='break')
        recipe=create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)
        payload = {'tags': []}
        url=detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        payload = {
            'title': 'Cauliflower Tacos',
            'description': 'Delicious tacos made with cauliflower.',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a new recipe with existing ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Lemon')
        payload = {
            'title': 'Vietnamese Soup',
            'description': 'A tangy soup made with lemon and fish sauce.',
            'time_minutes': 25,
            'price': '2.55',
            'ingredients': [{'name': 'Lemon'}, {'name': 'Fish Sauce'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    
    def test_update_recipe_with_ingredient(self):
        recipe = create_recipe(user=self.user)
        payload={'ingredient':'puppa'}
        url=detail_url(recipe.id)
        res=self.client.patch(url,payload,formart='json')
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        new_ingredient=Ingredient.objects.create(user=self.user,name='Lemon')
        recipe.ingredients.add(new_ingredient)  
        self.assertIn(new_ingredient,recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipes ingredients."""
        ingredient = Ingredient.objects.create(user=self.user, name='Garlic')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)


    
class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            print(f"Image file path: {image_file.name}")  # Add this to check file handling
            input()
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')
            print(res.data)

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)



    def test_filter_by_tags(self):
        r1=create_recipe(user=self.user,title='Recipe for person')
        r2=create_recipe(user=self.user,title='Recipe for another person')

        tag1=Tag.objects.create(user=self.user,name='data')
        tag2=Tag.objects.create(user=self.user,name='optimization')


        r1.tags.add(tag1)
        r2.tags.add(tag2)


        r3 = create_recipe(user=self.user, title='Fish and chips')

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data,res.data)
        self.assertIn(s2.data,res.data)
        self.assertNotIn(s3.data,res.data)

    def test_filter_by_ingredients(self):
        r1=create_recipe(user=self.user,title='Recipe for person')
        r2=create_recipe(user=self.user,title='Recipe for another person')

        ingredient1=Ingredient.objects.create(user=self.user,name='orange')
        ingredient2=Ingredient.objects.create(user=self.user,name='melon')


        r1.ingredients.add(ingredient1)
        r2.ingredients.add(ingredient2)


        r3 = create_recipe(user=self.user, title='Red Lentil Daal')

        params = {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data,res.data)
        self.assertIn(s2.data,res.data)
        self.assertNotIn(s3.data,res.data)

















    




























  






        















    



