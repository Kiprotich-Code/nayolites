"""
Staff portal views for the CourseContent domain.
All views use StaffRequiredMixin + explicit permission_required.
"""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.mixins import StaffRequiredMixin
from apps.core.audit import audit_log
from apps.core.models import AuditAction
from apps.courses.models import Course

from .forms import CourseContentForm
from .models import CourseContent, ContentVisibility


class ContentListView(StaffRequiredMixin, View):
    permission_required = 'content.view_coursecontent'

    def get(self, request):
        qs = CourseContent.objects.select_related(
            'course', 'course_unit', 'uploaded_by'
        ).order_by('-created_at')

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(course__code__icontains=q)
                | Q(course__name__icontains=q)
                | Q(course_unit__code__icontains=q)
            )

        course_filter = request.GET.get('course', '')
        if course_filter:
            qs = qs.filter(course_id=course_filter)

        visibility_filter = request.GET.get('visibility', '')
        if visibility_filter:
            qs = qs.filter(visibility=visibility_filter)

        paginator = Paginator(qs, 25)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'staff/content/list.html', {
            'page_title': 'Course Content',
            'active_section': 'content',
            'page_obj': page_obj,
            'q': q,
            'course_filter': course_filter,
            'visibility_filter': visibility_filter,
            'visibility_choices': ContentVisibility.choices,
            'courses': Course.objects.filter(is_active=True).order_by('name'),
            'total': qs.count(),
            'can_add': request.user.has_perm('content.add_coursecontent'),
        })


class ContentCreateView(StaffRequiredMixin, View):
    permission_required = 'content.add_coursecontent'

    def get(self, request):
        return render(request, 'staff/content/form.html', {
            'page_title': 'Upload Content',
            'active_section': 'content',
            'form': CourseContentForm(),
            'action': 'create',
        })

    def post(self, request):
        form = CourseContentForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.uploaded_by = request.user
            item.save()
            audit_log(
                actor=request.user,
                action=AuditAction.CONTENT_UPLOADED,
                obj=item,
                description=f'Content uploaded: {item}',
                request=request,
            )
            messages.success(request, f'"{item.title}" uploaded successfully.')
            return redirect('staff:content_detail', pk=item.pk)
        return render(request, 'staff/content/form.html', {
            'page_title': 'Upload Content',
            'active_section': 'content',
            'form': form,
            'action': 'create',
        })


class ContentDetailView(StaffRequiredMixin, View):
    permission_required = 'content.view_coursecontent'

    def get(self, request, pk):
        item = get_object_or_404(
            CourseContent.objects.select_related('course', 'course_unit', 'uploaded_by'),
            pk=pk,
        )
        return render(request, 'staff/content/detail.html', {
            'page_title': item.title,
            'active_section': 'content',
            'item': item,
            'can_edit': request.user.has_perm('content.change_coursecontent'),
            'can_delete': request.user.has_perm('content.delete_coursecontent'),
        })


class ContentEditView(StaffRequiredMixin, View):
    permission_required = 'content.change_coursecontent'

    def get(self, request, pk):
        item = get_object_or_404(CourseContent, pk=pk)
        return render(request, 'staff/content/form.html', {
            'page_title': f'Edit: {item.title}',
            'active_section': 'content',
            'form': CourseContentForm(instance=item),
            'item': item,
            'action': 'edit',
        })

    def post(self, request, pk):
        item = get_object_or_404(CourseContent, pk=pk)
        form = CourseContentForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            item = form.save()
            audit_log(
                actor=request.user,
                action=AuditAction.CONTENT_UPDATED,
                obj=item,
                description=f'Content updated: {item}',
                request=request,
            )
            messages.success(request, f'"{item.title}" updated.')
            return redirect('staff:content_detail', pk=item.pk)
        return render(request, 'staff/content/form.html', {
            'page_title': f'Edit: {item.title}',
            'active_section': 'content',
            'form': form,
            'item': item,
            'action': 'edit',
        })


class ContentDeleteView(StaffRequiredMixin, View):
    permission_required = 'content.delete_coursecontent'

    def get(self, request, pk):
        item = get_object_or_404(CourseContent, pk=pk)
        return render(request, 'staff/content/confirm_delete.html', {
            'page_title': f'Delete: {item.title}',
            'active_section': 'content',
            'item': item,
        })

    def post(self, request, pk):
        item = get_object_or_404(CourseContent, pk=pk)
        title = item.title
        course_code = item.course.code
        # Delete the file from storage if present
        if item.file:
            item.file.delete(save=False)
        audit_log(
            actor=request.user,
            action=AuditAction.CONTENT_DELETED,
            obj=item,
            description=f'Content deleted: [{course_code}] {title}',
            request=request,
        )
        item.delete()
        messages.success(request, f'"{title}" deleted.')
        return redirect('staff:content')
