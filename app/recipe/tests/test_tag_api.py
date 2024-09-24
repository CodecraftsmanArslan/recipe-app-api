from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from decimal import Decimal
from rest_framework.test import APIClient

from core.models import Tag,Recipe

from recipe.serializers import TagSerializer



TAGs_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    """Return recipe detail URL"""
    return reverse('recipe:tag-detail', args=[tag_id])

def create_user(email='test@email.com', password='testpass123'):
    """Helper function to create a user"""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicRecipeAPITests(TestCase):
    
    
    def setUp(self):
        self.client=APIClient()

    def test_auth_required(self):

        res=self.client.get(TAGs_URL)
        self.assertEqual(res.status_code,status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeApiTests(TestCase):
    
    def setUp(self):
        self.client=APIClient()
        self.user=create_user()
        self.client.force_authenticate(self.user)


    def test_create_tag(self):
        Tag.objects.create(user=self.user,name='Tag1')
        Tag.objects.create(user=self.user,name='Tag2')

        res=self.client.get(TAGs_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag=Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tag, many=True)
        self.assertEqual(res.data,serializer.data)

    def test_create_limited_to_user(self):

        user2=create_user(email='other@example.com')
        Tag.objects.create(user=user2,name='recipe')
        tag=Tag.objects.create(user=self.user,name='ingredient')

        res=self.client.get(TAGs_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)


    def test_update_tag(self):
        tag=Tag.objects.create(user=self.user,name='Tag1')
        payload={'name':'recipent'}
        url=detail_url(tag.id)
        res=self.client.put(url,payload)
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    

    def test_delete_tag(self):
        tag=Tag.objects.create(user=self.user,name='Tag1')
        url=detail_url(tag.id)
        res=self.client.delete(url)
        self.assertEqual(res.status_code,status.HTTP_204_NO_CONTENT)
        tags=Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())


    def test_filter_tags_assigned_to_recipes(self):
        """Test listing tags to those assigned to recipes."""
        tag1 = Tag.objects.create(user=self.user, name='Breakfast')
        tag2 = Tag.objects.create(user=self.user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Green Eggs on Toast',
            time_minutes=10,
            price=Decimal('2.50'),
            user=self.user,
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGs_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    

    def test_filter_tags_unique(self):
        t1=Tag.objects.create(user=self.user,name='Tag1')
        Tag.objects.create(user=self.user,name='Tag2')

        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Herb Eggs',
            time_minutes=20,
            price=Decimal('4.00'),
            user=self.user,
        )

        recipe1.tags.add(t1)
        recipe2.tags.add(t1)


        res=self.client.get(TAGs_URL,{'assigned_only': 1})
        
        self.assertEqual(len(res.data),1)











    





       









