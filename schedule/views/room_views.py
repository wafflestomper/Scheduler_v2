from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from ..models import Room
from django.db import transaction


def view_rooms(request):
    """View all rooms."""
    rooms = Room.objects.all().order_by('number')
    return render(request, 'schedule/view_rooms.html', {'rooms': rooms})


def create_room(request):
    """Create a new room."""
    if request.method == 'POST':
        number = request.POST.get('number')
        capacity = request.POST.get('capacity')
        room_type = request.POST.get('type', 'classroom')
        
        try:
            # Validate input
            if not number:
                raise ValueError("Room number is required")
            
            try:
                capacity = int(capacity) if capacity else 30  # Default capacity of 30
                if capacity <= 0:
                    raise ValueError("Capacity must be a positive number")
            except ValueError:
                raise ValueError("Capacity must be a valid number")
            
            # Create the room
            with transaction.atomic():
                # Generate a room ID based on the room number
                room_id = f"R{Room.objects.count() + 1:03d}"
                
                room = Room(
                    id=room_id,
                    number=number,
                    capacity=capacity,
                    type=room_type
                )
                room.save()
                
                messages.success(request, f"Room '{number}' created successfully!")
                return redirect('view_rooms')
                
        except ValueError as e:
            messages.error(request, str(e))
            
    # For GET request or if there was an error in POST
    return render(request, 'schedule/create_room.html', {
        'room_types': Room.ROOM_TYPES
    })


def edit_room(request, room_id):
    """Edit an existing room."""
    room = get_object_or_404(Room, pk=room_id)
    
    if request.method == 'POST':
        number = request.POST.get('number')
        capacity = request.POST.get('capacity')
        room_type = request.POST.get('type', 'classroom')
        
        try:
            # Validate input
            if not number:
                raise ValueError("Room number is required")
            
            try:
                capacity = int(capacity) if capacity else 30
                if capacity <= 0:
                    raise ValueError("Capacity must be a positive number")
            except ValueError:
                raise ValueError("Capacity must be a valid number")
            
            # Update the room
            with transaction.atomic():
                room.number = number
                room.capacity = capacity
                room.type = room_type
                room.save()
                
                messages.success(request, f"Room '{number}' updated successfully!")
                return redirect('view_rooms')
                
        except ValueError as e:
            messages.error(request, str(e))
    
    # For GET request or if there was an error in POST
    return render(request, 'schedule/edit_room.html', {
        'room': room,
        'room_types': Room.ROOM_TYPES
    })


def delete_room(request, room_id):
    """Delete a room."""
    room = get_object_or_404(Room, pk=room_id)
    
    if request.method == 'POST':
        # Check if there are any sections using this room
        from ..models import Section
        if Section.objects.filter(room=room).exists():
            messages.error(request, f"Cannot delete room '{room.number}' because it has sections assigned to it.")
            return redirect('view_rooms')
        
        room_number = room.number
        room.delete()
        messages.success(request, f"Room '{room_number}' deleted successfully!")
        return redirect('view_rooms')
    
    return render(request, 'schedule/delete_room_confirm.html', {'room': room}) 