from rest_framework import serializers
from .models import ReportInstance

class ReportInstanceSerializer(serializers.ModelSerializer):
    report_title = serializers.CharField(source="report.title", read_only=True)

    class Meta:
        model = ReportInstance
        fields = [
            "id",
            "report_title",
            "instance_summary",
            "date_of_the_report",
            "address_of_the_doctor",
            "name_of_the_doctor",
            "json",
            "file",
            "youtube_videos",
        ]
