from django.contrib import admin
from .models import Appointment, WaitlistEntry
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
# Register your models here.

class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "doctor_name",
        "patient_name",
        "scheduled_date",
        "time",
        "appointment_type",
        "appointment_status",
        "cancel",
    ]
    list_filter = [
        "appointment_status",
        "appointment_type",
        "scheduled_date",
        "cancel",
    ]
    search_fields = [
        "doctor__user__first_name",
        "doctor__user__last_name",
        "patient__user__first_name",
        "patient__user__last_name",
    ]
    list_select_related = ["doctor__user", "patient__user", "time"]

    def doctor_name(self,obj):
        return obj.doctor.user.first_name
    def patient_name(self,obj):
        return obj.patient.user.first_name
    def save_model(self,request,obj,form,change):
        super().save_model(request, obj, form, change)
        if obj.appointment_status == "Running" and obj.appointment_type == "Online":
            email_subject = "Your Appointment is Running"
            email_body = render_to_string('appointmentEmail.html',{'user':obj.patient.user,'doctor':obj.doctor})
            email = EmailMultiAlternatives(email_subject,'',to=[obj.patient.user.email])
            email.attach_alternative(email_body,"text/html")
            email.send(fail_silently=True)

admin.site.register(Appointment,AppointmentAdmin)


class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ["patient", "doctor", "requested_date", "time", "status"]
    list_filter = ["status", "requested_date"]
    search_fields = [
        "patient__user__first_name",
        "patient__user__last_name",
        "doctor__user__last_name",
    ]
    list_select_related = ["patient__user", "doctor__user", "time"]

admin.site.register(WaitlistEntry, WaitlistEntryAdmin)
