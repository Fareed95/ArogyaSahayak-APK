from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from utils.usercheck import authenticate_request
from .diet import ProductAnalysis
from .scanning import scan_barcode_and_number

# Create your views here.
class DietViewSet(APIView):
    def post(self, request, format=None):
        user = authenticate_request(request, need_user=True)
        image = request.FILES.get("image")
        if not image:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
        try :
            barcode = scan_barcode_and_number(image)
            print(barcode)
        except Exception as e:
            return Response({"error": f"Error scanning image: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        if not barcode:
            return Response({"error": "No barcode or number found in the image"}, status=status.HTTP_400_BAD_REQUEST)
        analysis = ProductAnalysis(barcode)
        print(analysis)
        analysis.fetch_data()
        if not analysis.product_data:
            return Response({"error": "Failed to retrieve product data"}, status=status.HTTP_400_BAD_REQUEST) 
        response_data = {
            "product_name": analysis.get_product_name(),
            "product_values": analysis.product_values,
            "healthy_reasons": analysis.healthy_reasons,
            "unhealthy_reasons": analysis.unhealthy_reasons,
            "verdict": analysis.show_results(),
            "reasons": analysis.show_reasons(),
        }


        return Response(response_data, status=status.HTTP_200_OK)
