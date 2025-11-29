# reports/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from authentication.models import User
from .serializers import ReportInstanceSerializer
from utils.usercheck import authenticate_request
import os
from .models import Report, ChatBot, ReportInstance
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import json
from .models import Report, ReportInstance
from .agents.extracting_basic_details import extract_report_from_pdf, generate_report_summary as generate_basic_summary
from .agents.extracting_json_details import extract_medical_from_pdf, generate_report_summary as generate_json_summary
from .agents.overal_summary import generate_final_summary
from .agents.yoga_prompt import get_youtube_query
from .agents.youtube_scrapping import youtube_search
class UploadReportView(APIView):
    """
    Upload PDF, extract report details, save to Report & ReportInstance.
    If a report with the same title already exists for the user, only a new instance is created,
    and the report's overall_summary is updated.
    """

    def post(self, request, format=None):
        user = authenticate_request(request, need_user=True)
        title = request.data.get("title", "Untitled Report")
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if report with same title already exists for the user
        report, created = Report.objects.get_or_create(user=user, title=title)

        # Save the uploaded PDF temporarily
        temp_path = default_storage.save(f"temp/{uploaded_file.name}", uploaded_file)
        full_path = default_storage.path(temp_path)

        try:
            # -------------------------------
            # Extract structured report details
            # -------------------------------
            page_reports = extract_report_from_pdf(full_path)
            structured_json = [r.dict() for r in page_reports]
            basic_summary = generate_basic_summary(page_reports)

            # -------------------------------
            # Extract test results JSON
            # -------------------------------
            page_results = extract_medical_from_pdf(full_path)
            test_json = [r.dict() for r in page_results]
            test_summary = generate_json_summary(page_results)

            # -------------------------------
            # Polished final summary using OpenAI
            # -------------------------------
            final_summary_text = generate_final_summary(
                basic_details=structured_json[0].get("details") if structured_json else {},
                summary=f"{basic_summary}\n\n{test_summary}"
            )
            youtube_query = get_youtube_query(final_summary_text)
            youtube_results_json = youtube_search(youtube_query, max_results=5)
            # -------------------------------
            # Save ReportInstance (without instance_name)
            # -------------------------------
            instance = ReportInstance.objects.create(
                report=report,
                file=uploaded_file.name,
                json={
                    "structured_details": structured_json,
                    "test_details": test_json
                },
                instance_summary=final_summary_text,
                youtube_videos=json.loads(youtube_results_json),
                name_of_the_doctor=page_reports[0].details.doctor_name if page_reports else "",
                address_of_the_doctor=page_reports[0].details.hospital_address if page_reports else ""
            )

            # Update Report's overall_summary
            report.overall_summary = final_summary_text
            report.save()

            return Response({
                "report_id": report.id,
                "instance_id": instance.id,
                "message": "Report uploaded and processed successfully.",
                "final_summary": final_summary_text,
                "structured_json": structured_json,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if os.path.exists(full_path):
                os.remove(full_path)


class UploadReportViewTelegram(APIView):
    """
    Upload PDF, extract report details, save to Report & ReportInstance.
    If a report with the same title already exists for the user, only a new instance is created,
    and the report's overall_summary is updated.
    """

    def post(self, request, format=None):
        phone = request.data.get("phone")
        user = User.objects.filter(phone_number=phone).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        title = request.data.get("title", "Untitled Report")
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if report with same title already exists for the user
        report, created = Report.objects.get_or_create(user=user, title=title)

        # Save the uploaded PDF temporarily
        temp_path = default_storage.save(f"temp/{uploaded_file.name}", uploaded_file)
        full_path = default_storage.path(temp_path)

        try:
            # -------------------------------
            # Extract structured report details
            # -------------------------------
            page_reports = extract_report_from_pdf(full_path)
            structured_json = [r.dict() for r in page_reports]
            basic_summary = generate_basic_summary(page_reports)

            # -------------------------------
            # Extract test results JSON
            # -------------------------------
            page_results = extract_medical_from_pdf(full_path)
            test_json = [r.dict() for r in page_results]
            test_summary = generate_json_summary(page_results)

            # -------------------------------
            # Polished final summary using OpenAI
            # -------------------------------
            final_summary_text = generate_final_summary(
                basic_details=structured_json[0].get("details") if structured_json else {},
                summary=f"{basic_summary}\n\n{test_summary}"
            )
            youtube_query = get_youtube_query(final_summary_text)
            youtube_results_json = youtube_search(youtube_query, max_results=5)
            # -------------------------------
            # Save ReportInstance (without instance_name)
            # -------------------------------
            instance = ReportInstance.objects.create(
                report=report,
                file=uploaded_file.name,
                json={
                    "structured_details": structured_json,
                    "test_details": test_json
                },
                instance_summary=final_summary_text,
                youtube_videos=json.loads(youtube_results_json),
                name_of_the_doctor=page_reports[0].details.doctor_name if page_reports else "",
                address_of_the_doctor=page_reports[0].details.hospital_address if page_reports else ""
            )

            # Update Report's overall_summary
            report.overall_summary = final_summary_text
            report.save()

            return Response({
                "report_id": report.id,
                "instance_id": instance.id,
                "message": "Report uploaded and processed successfully.",
                "final_summary": final_summary_text,
                "structured_json": structured_json,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if os.path.exists(full_path):
                os.remove(full_path)



MAX_HISTORY = 10

class UserChatBotAPIView(APIView):

    def post(self, request):
        user = authenticate_request(request, need_user=True)
        print(user)
    
        user_message = request.data.get("message", "").strip()
        print(user_message)
        if not user_message:
            return Response({"error": "Message is required"}, status=400)

        # Merge user's report summaries as **background knowledge**
        reports = Report.objects.filter(user=user)
        merged_summary = " ".join([r.overall_summary or "" for r in reports])

        # Get or create ChatBot instance
        chatbot, _ = ChatBot.objects.get_or_create(user=user)

        # Load existing memory
        try:
            history = json.loads(chatbot.memory) if chatbot.memory else []
        except json.JSONDecodeError:
            history = []

        # Keep last 10 messages
        history = history[-MAX_HISTORY:]

        # Build messages for LangChain
        messages = []

        # System message: background context + instructions
        system_prompt = (
            f"You are a helpful personal health assistant. "
            f"You have access to the user's health information (summarized) "
            f"for context, but you must never reveal raw report details. "
            f"Provide advice, suggestions, or answer questions about health, "
            f"nutrition, and wellbeing in a friendly, personalized way. "
            f"User's health summary (for reference only, do not show to user): {merged_summary}"
        )
        messages.append(SystemMessage(content=system_prompt))

        # Append previous conversation history
        for msg in history:
            if msg["role"] == "human":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # Append current user message
        messages.append(HumanMessage(content=user_message))

        # Initialize LangChain chat
        chat = ChatOpenAI(model="gpt-4")
        ai_response = chat(messages)

        # Append AI response to history
        history.append({"role": "human", "content": user_message})
        history.append({"role": "ai", "content": ai_response.content})
        history = history[-MAX_HISTORY:]  # keep last 10 messages

        # Save back to ChatBot memory
        chatbot.memory = json.dumps(history)
        chatbot.save()

        return Response({"response": ai_response.content})
    

class UserReportInstancesView(APIView):


    def post(self, request):
        """
        POST: user ka email bhejo aur uske report instances return honge
        """
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        instances = ReportInstance.objects.filter(report__user=user)
        serializer = ReportInstanceSerializer(instances, many=True)

        return Response({
            "email": user.email,
            "report_instances": serializer.data
        }, status=status.HTTP_200_OK)

    def get(self, request):
        """
        GET: 
        - Agar pk diya hai: sirf us report instance ka data return hoga
        - Agar pk nahi diya: sabhi authenticated user ke report instances return honge
        """
        user = authenticate_request(request, need_user=True)
        if not user:
            return Response({"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED)

        pk = request.query_params.get("pk")  # GET query parameter
        if pk:
            try:
                instance = ReportInstance.objects.get(pk=pk, report__user=user)
            except ReportInstance.DoesNotExist:
                return Response({"error": "Report instance not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ReportInstanceSerializer(instance)
            return Response({
                "email": user.email,
                "report_instance": serializer.data
            }, status=status.HTTP_200_OK)
        
        # Agar pk nahi diya, sabhi instances return karo
        instances = ReportInstance.objects.filter(report__user=user)
        serializer = ReportInstanceSerializer(instances, many=True)

        return Response({
            "email": user.email,
            "report_instances": serializer.data
        }, status=status.HTTP_200_OK)
