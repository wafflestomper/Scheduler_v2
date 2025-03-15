from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Room
from django.db import transaction


def view_rooms(request):
    """View all rooms."""
    rooms = Room.objects.all().order_by('name')
    return render(request, 'schedule/rooms/view_rooms.html', {'rooms': rooms})


def create_room(request):
    """Create a new room."""
    if request.method == 'POST':
        name = request.POST.get('name')
        capacity = request.POST.get('capacity')
        room_type = request.POST.get('room_type', '')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Room name is required")
            
            try:
                capacity = int(capacity) if capacity else 30  # Default capacity of 30
                if capacity <= 0:
                    raise ValueError("Capacity must be a positive number")
            except ValueError:
                raise ValueError("Capacity must be a valid number")
            
            # Create the room
            with transaction.atomic():
                room = Room(
                    name=name,
                    capacity=capacity,
                    room_type=room_type
                )
                room.save()
                
                messages.success(request, f"Room '{name}' created successfully!")
                return redirect('view_rooms')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/rooms/create_room.html', {
        'room_types': Room.ROOM_TYPES if hasattr(Room, 'ROOM_TYPES') else []
    })


def edit_room(request, room_id):
    """Edit an existing room."""
    room = get_object_or_404(Room, pk=room_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        capacity = request.POST.get('capacity')
        room_type = request.POST.get('room_type', '')
        
        try:
            # Validate input
            if not name:
                raise ValueError("Room name is required")
            
            try:
                capacity = int(capacity) if capacity else 30
                if capacity <= 0:
                    raise ValueError("Capacity must be a positive number")
            except ValueError:
                raise ValueError("Capacity must be a valid number")
            
            # Update the room
            with transaction.atomic():
                room.name = name
                room.capacity = capacity
                room.room_type = room_type
                room.save()
                
                messages.success(request, f"Room '{name}' updated successfully!")
                return redirect('view_rooms')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/rooms/edit_room.html', {
        'room': room,
        'room_types': Room.ROOM_TYPES if hasattr(Room, 'ROOM_TYPES') else []
    })


def delete_room(request, room_id):
    """Delete a room."""
    room = get_object_or_404(Room, pk=room_id)
    
    if request.method == 'POST':
        # Check if there are any sections using this room
        if room.section_set.exists():
            messages.error(request, f"Cannot delete room '{room.name}' because it has sections assigned to it.")
            return redirect('view_rooms')
        
        room_name = room.name
        room.delete()
        messages.success(request, f"Room '{room_name}' deleted successfully!")
        return redirect('view_rooms')
    
    return render(request, 'schedule/rooms/confirm_delete.html', {'room': room}) 