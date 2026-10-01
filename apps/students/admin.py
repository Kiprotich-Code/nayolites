from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'admission_number', 'county', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'admission_number')
    raw_id_fields = ('user',)
