from django.http import JsonResponse

def health_check(request):
    print("helloworld")
    return JsonResponse({"status": "ok"})
