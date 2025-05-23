from django.db.models import Q
from django.db.models.functions import Lower
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from adventures.models import Collection, Adventure, Transportation, Note, Category, Visit
from adventures.permissions import CollectionShared
from adventures.serializers import CollectionSerializer
from users.models import CustomUser as User
from datetime import datetime
from adventures.utils import pagination
import csv # Added
import io # Added

class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [CollectionShared]
    pagination_class = pagination.StandardResultsSetPagination

    # def get_queryset(self):
    #     return Collection.objects.filter(Q(user_id=self.request.user.id) & Q(is_archived=False))

    def apply_sorting(self, queryset):
        order_by = self.request.query_params.get('order_by', 'name')
        order_direction = self.request.query_params.get('order_direction', 'asc')

        valid_order_by = ['name', 'updated_at', 'start_date']
        if order_by not in valid_order_by:
            order_by = 'updated_at'

        if order_direction not in ['asc', 'desc']:
            order_direction = 'asc'

        # Apply case-insensitive sorting for the 'name' field
        if order_by == 'name':
            queryset = queryset.annotate(lower_name=Lower('name'))
            ordering = 'lower_name'
            if order_direction == 'desc':
                ordering = f'-{ordering}'
        elif order_by == 'start_date':
            ordering = 'start_date'
            if order_direction == 'asc':
                ordering = 'start_date'
            else:
                ordering = '-start_date'
        else:
            order_by == 'updated_at'
            ordering = 'updated_at'
            if order_direction == 'asc':
                ordering = '-updated_at'

        #print(f"Ordering by: {ordering}")  # For debugging

        return queryset.order_by(ordering)
    
    def list(self, request, *args, **kwargs):
        # make sure the user is authenticated
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Collection.objects.filter(user_id=request.user.id)
        queryset = self.apply_sorting(queryset)
        collections = self.paginate_and_respond(queryset, request)
        return collections
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user_id=request.user.id)
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
       
        queryset = Collection.objects.filter(
            Q(user_id=request.user.id) & Q(is_archived=True)
        )
        
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
       
        return Response(serializer.data)
    
    # this make the is_public field of the collection cascade to the adventures
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if 'collection' in serializer.validated_data:
            new_collection = serializer.validated_data['collection']
            # if the new collection is different from the old one and the user making the request is not the owner of the new collection return an error
            if new_collection != instance.collection and new_collection.user_id != request.user:
                return Response({"error": "User does not own the new collection"}, status=400)

        # Check if the 'is_public' field is present in the update data
        if 'is_public' in serializer.validated_data:
            new_public_status = serializer.validated_data['is_public']
            
            # if is_publuc has changed and the user is not the owner of the collection return an error
            if new_public_status != instance.is_public and instance.user_id != request.user:
                print(f"User {request.user.id} does not own the collection {instance.id} that is owned by {instance.user_id}")
                return Response({"error": "User does not own the collection"}, status=400)

            # Update associated adventures to match the collection's is_public status
            Adventure.objects.filter(collection=instance).update(is_public=new_public_status)

            # do the same for transportations
            Transportation.objects.filter(collection=instance).update(is_public=new_public_status)

            # do the same for notes
            Note.objects.filter(collection=instance).update(is_public=new_public_status)

            # Log the action (optional)
            action = "public" if new_public_status else "private"
            print(f"Collection {instance.id} and its adventures were set to {action}")

        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    # make an action to retreive all adventures that are shared with the user
    @action(detail=False, methods=['get'])
    def shared(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        queryset = Collection.objects.filter(
            shared_with=request.user
        )
        queryset = self.apply_sorting(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    # Adds a new user to the shared_with field of an adventure
    @action(detail=True, methods=['post'], url_path='share/(?P<uuid>[^/.]+)')
    def share(self, request, pk=None, uuid=None):
        collection = self.get_object()
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        try:
            user = User.objects.get(uuid=uuid, public_profile=True)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        if user == request.user:
            return Response({"error": "Cannot share with yourself"}, status=400)
        
        if collection.shared_with.filter(id=user.id).exists():
            return Response({"error": "Adventure is already shared with this user"}, status=400)
        
        collection.shared_with.add(user)
        collection.save()
        return Response({"success": f"Shared with {user.username}"})
    
    @action(detail=True, methods=['post'], url_path='unshare/(?P<uuid>[^/.]+)')
    def unshare(self, request, pk=None, uuid=None):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=400)
        collection = self.get_object()
        if not uuid:
            return Response({"error": "User UUID is required"}, status=400)
        try:
            user = User.objects.get(uuid=uuid, public_profile=True)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        if user == request.user:
            return Response({"error": "Cannot unshare with yourself"}, status=400)
        
        if not collection.shared_with.filter(id=user.id).exists():
            return Response({"error": "Collection is not shared with this user"}, status=400)
        
        collection.shared_with.remove(user)
        collection.save()
        return Response({"success": f"Unshared with {user.username}"})

    def get_queryset(self):
        if self.action == 'destroy':
            return Collection.objects.filter(user_id=self.request.user.id)
        
        if self.action in ['update', 'partial_update']:
            return Collection.objects.filter(
                Q(user_id=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        
        if self.action == 'retrieve':
            if not self.request.user.is_authenticated:
                return Collection.objects.filter(is_public=True)
            return Collection.objects.filter(
                Q(is_public=True) | Q(user_id=self.request.user.id) | Q(shared_with=self.request.user)
            ).distinct()
        
        # For list action, include collections owned by the user or shared with the user, that are not archived
        return Collection.objects.filter(
            (Q(user_id=self.request.user.id) | Q(shared_with=self.request.user)) & Q(is_archived=False)
        ).distinct()


    def perform_create(self, serializer):
        # This is ok because you cannot share a collection when creating it
        serializer.save(user_id=self.request.user)
    
    def paginate_and_respond(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def _create_activity_from_data(self, user, activity_data, collection_obj):
        """
        Helper method to create Adventure, Category, and Visit objects from a dictionary.
        """
        category_name = activity_data.get('category')
        category = None
        if category_name: # Ensure category_name is not empty or None
            category, _ = Category.objects.get_or_create(user_id=user, name__iexact=category_name, defaults={'name': category_name})


        adventure = Adventure.objects.create(
            user_id=user,
            collection=collection_obj,
            name=activity_data.get('name'),
            description=activity_data.get('description'),
            location=activity_data.get('location'),
            category=category,
        )

        date_str = activity_data.get('date')
        if date_str: # Ensure date_str is not empty or None
            # Assuming date is in YYYY-MM-DD format
            activity_date = datetime.strptime(str(date_str).strip(), '%Y-%m-%d').date()
            Visit.objects.create(
                adventure=adventure,
                start_date=activity_date,
                end_date=activity_date,
                user_id=user,
            )
        return adventure

    @action(detail=False, methods=['post'], url_path='import')
    @transaction.atomic
    def import_collection(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "User is not authenticated"}, status=status.HTTP_403_FORBIDDEN)

        activities = []
        content_type = request.content_type.split(';')[0].strip().lower() # Get main content type

        try:
            if content_type == 'application/json':
                data = request.data
                activities_data = data.get('activities', [])
                # For JSON, activity_data is already a list of dicts
                for activity_item in activities_data:
                    # Ensure all expected keys are at least gettable with .get()
                    activities.append({
                        'name': activity_item.get('name'),
                        'description': activity_item.get('description'),
                        'location': activity_item.get('location'),
                        'date': activity_item.get('date'),
                        'category': activity_item.get('category'),
                    })

            elif content_type == 'text/csv' or content_type == 'application/csv':
                try:
                    csv_text = request.body.decode('utf-8')
                    csv_file = io.StringIO(csv_text)
                    reader = csv.DictReader(csv_file)
                    # Normalize fieldnames to lowercase for consistent access
                    reader.fieldnames = [name.strip().lower() for name in reader.fieldnames if name]
                    
                    required_headers = {'date', 'name'}
                    if not required_headers.issubset(set(reader.fieldnames or [])):
                        missing = required_headers - set(reader.fieldnames or [])
                        return Response({"error": f"CSV is missing required headers: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)

                    for row in reader:
                        # Ensure all expected keys are accessed safely
                        activities.append({
                            'name': row.get('name'),
                            'description': row.get('description'),
                            'location': row.get('location'),
                            'date': row.get('date'),
                            'category': row.get('category'),
                        })
                except csv.Error as e:
                    return Response({"error": f"CSV parsing error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
                except UnicodeDecodeError:
                    return Response({"error": "Invalid CSV file encoding. Please use UTF-8."}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"error": "Unsupported media type. Please use 'application/json' or 'text/csv'."}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

            if not activities:
                return Response({"error": "No activities provided or data is empty."}, status=status.HTTP_400_BAD_REQUEST)

            collection_name = f"Imported Collection - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            collection = Collection.objects.create(user_id=request.user, name=collection_name)

            for activity_data in activities:
                # Basic validation for required fields from CSV
                if content_type in ['text/csv', 'application/csv']:
                    if not activity_data.get('name') or not activity_data.get('date'):
                        # Log this or add to a list of errors to return, for now skipping
                        # Or, decide to fail the whole import:
                        # return Response({"error": f"Missing required field 'name' or 'date' in CSV row: {activity_data}"}, status=status.HTTP_400_BAD_REQUEST)
                        continue # Skip row if critical data is missing

                self._create_activity_from_data(request.user, activity_data, collection)
            
            # Refresh collection to get related adventures for serialization
            collection.refresh_from_db()
            serializer = CollectionSerializer(collection, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e: # Catches date parsing errors specifically from _create_activity_from_data
            return Response({"error": f"Data validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log the exception e for debugging
            print(f"Unhandled exception in import_collection: {e}") # Basic logging
            return Response({"error": "An unexpected error occurred during import."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
