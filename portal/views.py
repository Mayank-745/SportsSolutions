from django.shortcuts import render
from django.http import request
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .models import UserProfile
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import LessonPayment
import json
from .models import Course, UserCourseUnlock

# Create your views here.
def home(request):
    return render(request, 'index.html')

def lms(request):
    return render(request, 'lms.html')

def event1(request):
    return render(request, 'event1.html')


# In views.py, replace the old 'portal' view with this one.

def portal(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # --- THE FIX STARTS HERE ---

    # 1. Get the list of unlocked course IDs for the logged-in user.
    unlocked_course_ids = []
    try:
        # Query the UserCourseUnlock table for all unlocks belonging to this user
        user_unlocks = UserCourseUnlock.objects.filter(user=request.user)
        # Create a simple list of the course ID strings (e.g., ['course-1', 'course-2'])
        unlocked_course_ids = [unlock.course.course_id_str for unlock in user_unlocks]
    except Exception as e:
        print(f"Could not fetch user course unlocks: {e}")
        # Continue with an empty list if there's an error

    # 2. Get the user's role.
    try:
        role = request.user.userprofile.role
    except UserProfile.DoesNotExist:
        role = 'athlete'  # A sensible fallback

    # 3. Prepare the context dictionary for the template.
    context = {
        'user': request.user,
        'role': role,
        # This is the crucial variable your template needs.
        # We convert the Python list to a JSON string.
        'unlocked_course_ids_json': json.dumps(unlocked_course_ids),
        'razorpay_key': settings.RAZORPAY_KEY_ID
    }
    
    return render(request, 'portal.html', context)

    # --- THE FIX ENDS HERE ---



def sign(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST.get('role', '').strip().lower()
        if not role:
            messages.error(request, "Please select a role (Coach or Athlete).")
            return redirect('sign')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(user=user, role=role)
            messages.success(request, 'Account created successfully')
            return redirect('login')
    return render(request, 'signup.html')

def log_in(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/portal')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST.get('role', '').strip().lower()
        if not role:
            messages.error(request, "Please select a role (Coach or Athlete).")
            return redirect('register')

        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(user=user, role=role)
            messages.success(request, 'Account created successfully')
            return redirect('login')
    return render(request, 'register.html')

# In your views.py file

def create_order(request ):
    if request.method == "POST":
        try:
            # Load the request body and get the amount
            data = json.loads(request.body)
            amount_in_rupees = int(data.get('amount'))
            amount_in_paise = amount_in_rupees * 100 # Convert to paise
        except Exception as e:
            return JsonResponse({'status': 'failure', 'error': 'Invalid amount provided'}, status=400)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": "1"
        }
        
        try:
            order = client.order.create(order_data)
            return JsonResponse(order)
        except Exception as e:
            return JsonResponse({'status': 'failure', 'error': str(e)}, status=500)
            
    return JsonResponse({'status': 'failure', 'error': 'Invalid request method'}, status=405)

    


# In your views.py

# In your views.py

def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({'status': 'invalid method'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'unauthorized'}, status=401)

    try:
        data = json.loads(request.body)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # --- Step 1: Verify the payment signature ---
        params_dict = {
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        }
        # This will raise an error if the signature is not valid
        client.utility.verify_payment_signature(params_dict)
        
        # --- Step 2: THE FIX - Create the permanent course unlock record ---
        try:
            # Find the course the user paid for in your database.
            course_to_unlock = Course.objects.get(course_id_str=data['course_id'])

            # Create the unlock record. get_or_create is safe and prevents duplicates.
            unlock, created = UserCourseUnlock.objects.get_or_create(
                user=request.user,
                course=course_to_unlock
            )

            if created:
                print(f"SUCCESS: Created unlock record for user '{request.user.username}' for course '{course_to_unlock.name}'")
            else:
                print(f"INFO: Unlock record already existed for user '{request.user.username}' for course '{course_to_unlock.name}'")

        except Course.DoesNotExist:
            # This is a critical error. The frontend sent a course_id that isn't in your DB.
            print(f"CRITICAL ERROR: Course with course_id_str='{data['course_id']}' not found in the database.")
            return JsonResponse({'status': 'failure', 'error': 'Course not found.'}, status=404)
        except Exception as db_error:
            # Catch potential database errors during the unlock process
            print(f"DATABASE ERROR during course unlock: {str(db_error)}")
            return JsonResponse({'status': 'failure', 'error': 'Could not save course unlock.'}, status=500)

        # --- Step 3: (Optional but Recommended) Record the transaction for history ---
        LessonPayment.objects.update_or_create(
            user=request.user,
            course_id=data['course_id'],
            lesson_index=0, # Using 0 since we are unlocking a whole course.
            razorpay_order_id=data['razorpay_order_id'],
            defaults={
                'razorpay_payment_id': data['razorpay_payment_id'],
                'verified': True
            }
        )
        
        return JsonResponse({'status': 'success', 'message': 'Payment verified and course unlocked!'})

    except razorpay.errors.SignatureVerificationError as e:
        # This specifically catches the error if Razorpay's signature is invalid.
        print(f"SIGNATURE VERIFICATION FAILED: {str(e)}")
        return JsonResponse({'status': 'failure', 'error': 'Payment signature verification failed.'}, status=400)
    except Exception as e:
        # This will catch any other errors (e.g., JSON parsing, missing keys).
        print(f"An unexpected error occurred in verify_payment: {str(e)}")
        return JsonResponse({'status': 'failure', 'error': 'An unexpected error occurred.'}, status=400)

