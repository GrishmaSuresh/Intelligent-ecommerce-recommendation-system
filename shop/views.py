from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Product, Circle, Message, Purchase, ProductFeedback
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def product_list(request):
    products = Product.objects.all()
    for product in products:
        # Safely check if purchased by user's circle
        if request.user.is_authenticated:
            product.is_purchased_in_circle = product.purchased_by_any_in_circle(request.user)
        else:
            product.is_purchased_in_circle = False
    return render(request, 'shop/product_list.html', {'products': products})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    purchased_by_circle = False
    relation = None

    if request.user.is_authenticated:
        # Check if any circle member purchased it
        circle_members = Circle.objects.filter(owner=request.user)
        for circle in circle_members:
            if Purchase.objects.filter(user=circle.member, product=product).exists():
                purchased_by_circle = True
                relation = circle.relation or circle.member.username
                break

    context = {
        'product': product,
        'purchased_by_circle': purchased_by_circle,
        'relation': relation
    }
    return render(request, 'shop/product_detail.html', context)


@login_required
@require_POST
def ask_my_circle(request):
    product_id = request.POST.get('product_id')
    message_text = request.POST.get('message', '').strip()
    recipients = request.POST.getlist('recipients[]')
    product = get_object_or_404(Product, pk=product_id)
    created = []
    for uid in recipients:
        try:
            recipient = User.objects.get(pk=uid)
        except User.DoesNotExist:
            continue
        msg = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            product=product,
            text=message_text
        )
        created.append(msg.id)
    return JsonResponse({'status': 'ok', 'created_message_ids': created})

@login_required
def get_my_circle(request):
    circle_qs = Circle.objects.filter(owner=request.user).select_related('member')
    members = [{'id': c.member.id, 'username': c.member.username} for c in circle_qs]
    return JsonResponse({'members': members})

def home(request):
    return render(request, 'shop/home.html')

def search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(name__icontains=query) if query else []

    # If user is logged in, check if anyone in their circle purchased each product
    if request.user.is_authenticated:
        for product in products:
            product.circle_purchase = None  # default: not purchased by circle

            # Find all circle members and their relations
            circle_members = Circle.objects.filter(owner=request.user)
            for circle in circle_members:
                # Check if this member purchased the product
                if Purchase.objects.filter(user=circle.member, product=product).exists():
                    product.circle_purchase = circle.relation or circle.member.username
                    break  # stop checking once found
    else:
        for product in products:
            product.circle_purchase = None

    return render(request, 'shop/search_results.html', {'products': products, 'query': query})

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('shop:register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('shop:register')

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        messages.success(request, "Account created successfully! Please log in.")
        return redirect('shop:login')

    return render(request, 'shop/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('shop:home')  # redirect to home or ask my circle
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('shop:login')

    return render(request, 'shop/login.html')


def logout_view(request):
    logout(request)
    return redirect('shop:login')


@login_required
def my_notifications(request):
    # Show only distinct products for which user has messages
    products = (
        Message.objects.filter(recipient=request.user)
        .select_related("product")
        .order_by("-created_at")
        .values("product_id", "product__name", "product__image", "product__price")
        .distinct()
    )
    return render(request, "shop/notifications.html", {"products": products})

@login_required
def chat_room(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    # Fetch all messages between the current user and their circle related to the product
    messages_qs = Message.objects.filter(
        product=product
    ).filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related("sender").order_by("created_at")

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            # Send to all members in the circle if current user is the owner
            circle_members = Circle.objects.filter(owner=request.user)
            if circle_members.exists():
                for member in circle_members:
                    Message.objects.create(
                        sender=request.user,
                        recipient=member.member,
                        product=product,
                        text=text,
                    )
            else:
                # If the user is a circle member, send only to the owner
                try:
                    owner_rel = Circle.objects.get(member=request.user)
                    Message.objects.create(
                        sender=request.user,
                        recipient=owner_rel.owner,
                        product=product,
                        text=text,
                    )
                except Circle.DoesNotExist:
                    pass
            return redirect("shop:chat_room", product_id=product.id)

    # Get like/dislike counts
    likes = ProductFeedback.objects.filter(product=product, reaction='like').count()
    dislikes = ProductFeedback.objects.filter(product=product, reaction='dislike').count()

    return render(request, "shop/chat_room.html", {
        "product": product,
        "messages": messages_qs,
        "likes": likes,
        "dislikes": dislikes
    })

@login_required
@require_POST
def react_to_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    reaction_type = request.POST.get("reaction")

    feedback, created = ProductFeedback.objects.update_or_create(
        product=product,
        user=request.user,
        defaults={"reaction": reaction_type},
    )
    return JsonResponse({"status": "ok", "reaction": feedback.reaction})


@login_required
def my_notifications(request):
    # Fetch unique product IDs where the user was involved
    product_ids = (
        Message.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
        .values_list("product_id", flat=True)
        .distinct()
    )

    # Then get unique product details using those IDs
    products = (
        Product.objects.filter(id__in=product_ids)
        .values("id", "name", "image", "price")
    )

    # Get feedback summary for each unique product
    feedback_summary = {}
    for p in products:
        pid = p["id"]
        likes = ProductFeedback.objects.filter(product_id=pid, reaction="like").count()
        dislikes = ProductFeedback.objects.filter(product_id=pid, reaction="dislike").count()
        feedback_summary[pid] = {"likes": likes, "dislikes": dislikes}

    return render(request, "shop/notifications.html", {
        "products": products,
        "feedback_summary": feedback_summary
    })
