"""Staff portal views for Nayolites."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse

STUDENTS = [
    {"pk":1,"admission":"NCC/2024/0147","name":"Amina Wanjiru Kariuki","course":"Diploma in Computer Science","year":2,"status":"Active","sc":"success","phone":"+254 712 345 678","email":"amina.kariuki@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Female","county":"Kiambu"},
    {"pk":2,"admission":"NCC/2024/0148","name":"Brian Otieno Odhiambo","course":"Diploma in Broadcast Media","year":1,"status":"Active","sc":"success","phone":"+254 723 456 789","email":"brian.odhiambo@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Male","county":"Kisumu"},
    {"pk":3,"admission":"NCC/2024/0149","name":"Catherine Njoki Muigai","course":"Certificate in Graphic Design","year":1,"status":"Active","sc":"success","phone":"+254 734 567 890","email":"catherine.muigai@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Female","county":"Nairobi"},
    {"pk":4,"admission":"NCC/2024/0150","name":"David Kipchoge Rotich","course":"Diploma in Computer Science","year":2,"status":"Active","sc":"success","phone":"+254 745 678 901","email":"david.rotich@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Male","county":"Uasin Gishu"},
    {"pk":5,"admission":"NCC/2024/0151","name":"Esther Wambui Ndung'u","course":"Diploma in IT Support","year":1,"status":"Active","sc":"success","phone":"+254 756 789 012","email":"esther.ndungu@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Female","county":"Nyeri"},
    {"pk":6,"admission":"NCC/2023/0098","name":"Felix Kamau Njoroge","course":"Diploma in Computer Science","year":2,"status":"Active","sc":"success","phone":"+254 767 890 123","email":"felix.njoroge@student.nayolites.ac.ke","enrolled":"9 Jan 2023","gender":"Male","county":"Kiambu"},
    {"pk":7,"admission":"NCC/2023/0099","name":"Grace Achieng Oloo","course":"Diploma in Broadcast Media","year":2,"status":"Active","sc":"success","phone":"+254 778 901 234","email":"grace.oloo@student.nayolites.ac.ke","enrolled":"9 Jan 2023","gender":"Female","county":"Siaya"},
    {"pk":8,"admission":"NCC/2024/0152","name":"Hassan Abdi Mohamed","course":"Certificate in Web Development","year":1,"status":"Active","sc":"success","phone":"+254 789 012 345","email":"hassan.mohamed@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Male","county":"Garissa"},
    {"pk":9,"admission":"NCC/2024/0153","name":"Irene Chebet Koech","course":"Diploma in Computer Science","year":1,"status":"Suspended","sc":"warning","phone":"+254 700 123 456","email":"irene.koech@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Female","county":"Kericho"},
    {"pk":10,"admission":"NCC/2023/0100","name":"James Mwangi Kamau","course":"Diploma in IT Support","year":2,"status":"Active","sc":"success","phone":"+254 711 234 567","email":"james.kamau@student.nayolites.ac.ke","enrolled":"9 Jan 2023","gender":"Male","county":"Murang'a"},
    {"pk":11,"admission":"NCC/2024/0154","name":"Joyce Auma Onyango","course":"Certificate in Graphic Design","year":1,"status":"Active","sc":"success","phone":"+254 722 345 678","email":"joyce.onyango@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Female","county":"Migori"},
    {"pk":12,"admission":"NCC/2023/0101","name":"Kevin Njuguna Gachoki","course":"Diploma in Computer Science","year":2,"status":"Completed","sc":"secondary","phone":"+254 733 456 789","email":"kevin.gachoki@student.nayolites.ac.ke","enrolled":"9 Jan 2023","gender":"Male","county":"Kiambu"},
    {"pk":13,"admission":"NCC/2024/0155","name":"Linda Nyambura Waweru","course":"Diploma in Broadcast Media","year":1,"status":"Active","sc":"success","phone":"+254 744 567 890","email":"linda.waweru@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Female","county":"Nyandarua"},
    {"pk":14,"admission":"NCC/2024/0156","name":"Michael Ochieng Otieno","course":"Certificate in Web Development","year":1,"status":"Active","sc":"success","phone":"+254 755 678 901","email":"michael.otieno@student.nayolites.ac.ke","enrolled":"14 Jan 2024","gender":"Male","county":"Homa Bay"},
    {"pk":15,"admission":"NCC/2023/0102","name":"Nancy Wanjiku Karanja","course":"Diploma in Computer Science","year":2,"status":"Active","sc":"success","phone":"+254 766 789 012","email":"nancy.karanja@student.nayolites.ac.ke","enrolled":"9 Jan 2023","gender":"Female","county":"Kiambu"},
]

COURSES = [
    {"pk":1,"code":"DCS","name":"Diploma in Computer Science","duration":"2 Years","category":"Computing","status":"Active","enrolled":287,"units":12},
    {"pk":2,"code":"DBM","name":"Diploma in Broadcast Media","duration":"2 Years","category":"Media","status":"Active","enrolled":198,"units":12},
    {"pk":3,"code":"CGD","name":"Certificate in Graphic Design","duration":"1 Year","category":"Design","status":"Active","enrolled":143,"units":6},
    {"pk":4,"code":"CWD","name":"Certificate in Web Development","duration":"1 Year","category":"Computing","status":"Active","enrolled":112,"units":6},
    {"pk":5,"code":"DIT","name":"Diploma in IT Support","duration":"2 Years","category":"Computing","status":"Active","enrolled":107,"units":12},
]

PERIODS = [
    {"pk":1,"name":"2025 Semester 1","start":"13 Jan 2025","end":"30 May 2025","status":"Active","sc":"success","enrolled":412},
    {"pk":2,"name":"2024 Semester 2","start":"8 Jul 2024","end":"29 Nov 2024","status":"Completed","sc":"secondary","enrolled":389},
    {"pk":3,"name":"2024 Semester 1","start":"15 Jan 2024","end":"31 May 2024","status":"Completed","sc":"secondary","enrolled":371},
    {"pk":4,"name":"2023 Semester 2","start":"10 Jul 2023","end":"24 Nov 2023","status":"Completed","sc":"secondary","enrolled":308},
]

ENROLLMENTS = [
    {"pk":1,"admission":"NCC/2024/0147","student":"Amina Wanjiru Kariuki","course":"Diploma in Computer Science","period":"2025 Semester 1","year":2,"status":"Active","sc":"success","enrolled_date":"13 Jan 2025"},
    {"pk":2,"admission":"NCC/2024/0148","student":"Brian Otieno Odhiambo","course":"Diploma in Broadcast Media","period":"2025 Semester 1","year":1,"status":"Active","sc":"success","enrolled_date":"13 Jan 2025"},
    {"pk":3,"admission":"NCC/2024/0149","student":"Catherine Njoki Muigai","course":"Certificate in Graphic Design","period":"2025 Semester 1","year":1,"status":"Active","sc":"success","enrolled_date":"14 Jan 2025"},
    {"pk":4,"admission":"NCC/2024/0150","student":"David Kipchoge Rotich","course":"Diploma in Computer Science","period":"2025 Semester 1","year":2,"status":"Active","sc":"success","enrolled_date":"13 Jan 2025"},
    {"pk":5,"admission":"NCC/2023/0098","student":"Felix Kamau Njoroge","course":"Diploma in Computer Science","period":"2025 Semester 1","year":2,"status":"Active","sc":"success","enrolled_date":"13 Jan 2025"},
]

INVOICES = [
    {"invoice_number":"INV-2025-0147-01","student":"Amina Wanjiru Kariuki","admission":"NCC/2024/0147","period":"2025 Semester 1","issue_date":"10 Jan 2025","due_date":"31 Jan 2025","total":24500,"paid":15000,"balance":9500,"status":"Partially Paid","sc":"warning"},
    {"invoice_number":"INV-2025-0148-01","student":"Brian Otieno Odhiambo","admission":"NCC/2024/0148","period":"2025 Semester 1","issue_date":"10 Jan 2025","due_date":"31 Jan 2025","total":28500,"paid":28500,"balance":0,"status":"Paid","sc":"success"},
    {"invoice_number":"INV-2025-0149-01","student":"Catherine Njoki Muigai","admission":"NCC/2024/0149","period":"2025 Semester 1","issue_date":"10 Jan 2025","due_date":"31 Jan 2025","total":23000,"paid":0,"balance":23000,"status":"Unpaid","sc":"danger"},
    {"invoice_number":"INV-2025-0150-01","student":"David Kipchoge Rotich","admission":"NCC/2024/0150","period":"2025 Semester 1","issue_date":"10 Jan 2025","due_date":"31 Jan 2025","total":24500,"paid":24500,"balance":0,"status":"Paid","sc":"success"},
    {"invoice_number":"INV-2025-0151-01","student":"Esther Wambui Ndungu","admission":"NCC/2024/0151","period":"2025 Semester 1","issue_date":"10 Jan 2025","due_date":"31 Jan 2025","total":23500,"paid":10000,"balance":13500,"status":"Partially Paid","sc":"warning"},
]

PAYMENTS = [
    {"pk":1,"receipt":"RCP-2025-00391","student":"Amina Wanjiru Kariuki","admission":"NCC/2024/0147","invoice":"INV-2025-0147-01","amount":15000,"method":"M-Pesa","reference":"QGT8RH2450","date":"28 Jan 2025","status":"Confirmed","sc":"success"},
    {"pk":2,"receipt":"RCP-2025-00392","student":"Brian Otieno Odhiambo","admission":"NCC/2024/0148","invoice":"INV-2025-0148-01","amount":28500,"method":"Bank Transfer","reference":"TRF-NAY-20250127","date":"27 Jan 2025","status":"Confirmed","sc":"success"},
    {"pk":3,"receipt":"RCP-2025-00393","student":"David Kipchoge Rotich","admission":"NCC/2024/0150","invoice":"INV-2025-0150-01","amount":24500,"method":"M-Pesa","reference":"PKL7MN9913","date":"26 Jan 2025","status":"Confirmed","sc":"success"},
    {"pk":4,"receipt":"RCP-2025-00394","student":"Esther Wambui Ndungu","admission":"NCC/2024/0151","invoice":"INV-2025-0151-01","amount":10000,"method":"M-Pesa","reference":"ABC1234567","date":"25 Jan 2025","status":"Confirmed","sc":"success"},
    {"pk":5,"receipt":"RCP-2025-00395","student":"Felix Kamau Njoroge","admission":"NCC/2023/0098","invoice":"INV-2025-0098-01","amount":24500,"method":"M-Pesa","reference":"XYZ9876543","date":"24 Jan 2025","status":"Confirmed","sc":"success"},
]

RESULTS = [
    {"pk":1,"student":"Amina Wanjiru Kariuki","admission":"NCC/2024/0147","unit_code":"DCS 201","unit_name":"Software Engineering","period":"2025 Semester 1","cat":None,"exam":None,"total":None,"grade":None,"status":"Draft","sc":"secondary"},
    {"pk":2,"student":"Brian Otieno Odhiambo","admission":"NCC/2024/0148","unit_code":"DBM 104","unit_name":"Television Production","period":"2024 Semester 2","cat":32,"exam":49,"total":81,"grade":"A-","status":"Published","sc":"success"},
    {"pk":3,"student":"Amina Wanjiru Kariuki","admission":"NCC/2024/0147","unit_code":"DCS 104","unit_name":"Data Structures and Algorithms","period":"2024 Semester 2","cat":35,"exam":51,"total":86,"grade":"A","status":"Published","sc":"success"},
    {"pk":4,"student":"Catherine Njoki Muigai","admission":"NCC/2024/0149","unit_code":"CGD 101","unit_name":"Principles of Design","period":"2024 Semester 2","cat":28,"exam":44,"total":72,"grade":"B","status":"Approved","sc":"info"},
    {"pk":5,"student":"David Kipchoge Rotich","admission":"NCC/2024/0150","unit_code":"DCS 104","unit_name":"Data Structures and Algorithms","period":"2024 Semester 2","cat":22,"exam":38,"total":60,"grade":"B-","status":"Review","sc":"warning"},
]

FEE_STRUCTURES = [
    {"pk":1,"name":"DCS Standard Fee 2025","course":"Diploma in Computer Science","period":"2025 Semester 1","status":"Active","items":[{"name":"Tuition Fee","amount":18000},{"name":"Materials Fee","amount":3000},{"name":"Examination Fee","amount":2500},{"name":"Student Activity Levy","amount":500},{"name":"Library Fee","amount":500}],"total":24500},
    {"pk":2,"name":"DBM Standard Fee 2025","course":"Diploma in Broadcast Media","period":"2025 Semester 1","status":"Active","items":[{"name":"Tuition Fee","amount":20000},{"name":"Materials Fee","amount":4000},{"name":"Examination Fee","amount":2500},{"name":"Student Activity Levy","amount":500},{"name":"Library Fee","amount":500}],"total":27500},
    {"pk":3,"name":"CGD Standard Fee 2025","course":"Certificate in Graphic Design","period":"2025 Semester 1","status":"Active","items":[{"name":"Tuition Fee","amount":14000},{"name":"Materials Fee","amount":5000},{"name":"Examination Fee","amount":2000},{"name":"Student Activity Levy","amount":500},{"name":"Library Fee","amount":500}],"total":22000},
]

CONTENT = [
    {"pk":1,"title":"Week 1 - Introduction to Software Engineering","unit":"DCS 201","unit_name":"Software Engineering","type":"PDF","size":"1.2 MB","uploaded":"14 Jan 2025","visibility":"Enrolled Students","uploader":"Mr. James Kamau"},
    {"pk":2,"title":"Week 2 - Requirements Engineering","unit":"DCS 201","unit_name":"Software Engineering","type":"PDF","size":"980 KB","uploaded":"21 Jan 2025","visibility":"Enrolled Students","uploader":"Mr. James Kamau"},
    {"pk":3,"title":"Week 1 - HTTP and Django Overview","unit":"DCS 202","unit_name":"Web Application Development","type":"PDF","size":"756 KB","uploaded":"14 Jan 2025","visibility":"Enrolled Students","uploader":"Ms. Linda Otieno"},
    {"pk":4,"title":"Agile Methodology Video Lecture","unit":"DCS 201","unit_name":"Software Engineering","type":"Video URL","size":"-","uploaded":"28 Jan 2025","visibility":"Enrolled Students","uploader":"Mr. James Kamau"},
]

USERS = [
    {"pk":1,"name":"Solomon Waweru Kimani","email":"s.kimani@nayolites.ac.ke","role":"Principal","groups":["Administrator"],"status":"Active","last_login":"Today 08:42"},
    {"pk":2,"name":"Florence Achieng Oduor","email":"f.oduor@nayolites.ac.ke","role":"Deputy Principal","groups":["Administrator","Academic Officer"],"status":"Active","last_login":"Today 09:15"},
    {"pk":3,"name":"Dennis Mwangi Kariuki","email":"d.kariuki@nayolites.ac.ke","role":"Finance Officer","groups":["Finance Officer"],"status":"Active","last_login":"Yesterday"},
    {"pk":4,"name":"James Kamau Njoroge","email":"j.kamau@nayolites.ac.ke","role":"Lecturer","groups":["Lecturer","Academic Officer"],"status":"Active","last_login":"Today 07:58"},
    {"pk":5,"name":"Linda Otieno Adhiambo","email":"l.otieno@nayolites.ac.ke","role":"Lecturer","groups":["Lecturer"],"status":"Active","last_login":"Yesterday"},
    {"pk":6,"name":"Grace Nyambura Mwangi","email":"g.mwangi@nayolites.ac.ke","role":"Head of Department","groups":["Academic Officer"],"status":"Active","last_login":"28 Jan 2025"},
    {"pk":7,"name":"Registrar Account","email":"registrar@nayolites.ac.ke","role":"Registrar","groups":["Registrar"],"status":"Active","last_login":"Today 10:01"},
]

AUDIT_LOG = [
    {"pk":1,"actor":"Solomon Waweru Kimani","action":"Published results","object":"DCS 104 - 2024 Semester 2","ip":"197.248.12.44","timestamp":"28 Jan 2025 14:32"},
    {"pk":2,"actor":"Florence Achieng Oduor","action":"Approved results","object":"DCS 104 - 2024 Semester 2","ip":"197.248.12.45","timestamp":"28 Jan 2025 13:18"},
    {"pk":3,"actor":"James Kamau Njoroge","action":"Submitted results for review","object":"DCS 104 - 2024 Semester 2","ip":"197.248.12.47","timestamp":"27 Jan 2025 16:45"},
    {"pk":4,"actor":"Dennis Mwangi Kariuki","action":"Confirmed payment","object":"RCP-2025-00391 - Amina Wanjiru Kariuki","ip":"197.248.12.46","timestamp":"28 Jan 2025 10:14"},
    {"pk":5,"actor":"Registrar Account","action":"Enrolled student","object":"Amina Wanjiru Kariuki - 2025 Semester 1","ip":"197.248.12.48","timestamp":"13 Jan 2025 09:02"},
    {"pk":6,"actor":"Solomon Waweru Kimani","action":"Created academic period","object":"2025 Semester 1","ip":"197.248.12.44","timestamp":"6 Jan 2025 11:30"},
    {"pk":7,"actor":"Dennis Mwangi Kariuki","action":"Updated fee structure","object":"DCS Standard Fee 2025","ip":"197.248.12.46","timestamp":"5 Jan 2025 14:22"},
]


def _base(title, section=""):
    return {"page_title": title, "active_section": section}


# ============================================================
# Real dashboard — Phase 8
# ============================================================

@login_required(login_url='/auth/login/')
def staff_dashboard(request):
    """
    Permission-aware, database-driven staff dashboard.
    Only shows sections the current user has permission to see.
    Does not fabricate statistics — all numbers come from the database.
    """
    from apps.students.models import StudentProfile, StudentStatus
    from apps.enrollments.models import Enrollment, EnrollmentStatus, AcademicPeriod
    from apps.courses.models import Course

    u = request.user
    ctx = _base("Dashboard", "dashboard")

    # Academic context — current active periods
    active_periods = AcademicPeriod.objects.filter(is_active=True).order_by('-start_date')
    ctx['active_periods'] = active_periods

    # Student stats (only if user can see students)
    if u.has_perm('students.view_studentprofile'):
        ctx['total_students'] = StudentProfile.objects.count()
        ctx['active_students'] = StudentProfile.objects.filter(status=StudentStatus.ACTIVE).count()
        ctx['recent_students'] = (
            StudentProfile.objects.select_related('user')
            .order_by('-created_at')[:5]
        )

    # Enrollment stats (only if user can see enrollments)
    if u.has_perm('enrollments.view_enrollment'):
        ctx['active_enrollments'] = Enrollment.objects.filter(
            status=EnrollmentStatus.ACTIVE
        ).count()
        ctx['pending_enrollments'] = Enrollment.objects.filter(
            status=EnrollmentStatus.PENDING
        ).count()
        ctx['recent_enrollments'] = (
            Enrollment.objects.select_related('student__user', 'course', 'academic_period')
            .order_by('-enrolled_at')[:5]
        )

    # Course stats
    if u.has_perm('courses.view_course'):
        ctx['total_courses'] = Course.objects.filter(is_active=True).count()

    return render(request, "staff/dashboard.html", ctx)


# ============================================================
# Stub views for academic sections — replaced by real CBVs
# These redirect to the new real views to avoid dead links.
# ============================================================

from django.views.generic import RedirectView

# The old function-based academic stubs are replaced by CBVs in the
# dedicated app view files. The URL conf now points directly to those CBVs.
# These stubs are kept only so the old prototype URL names don't crash
# if any template still references them — they redirect immediately.

@login_required(login_url='/auth/login/')
def staff_students(request):
    from django.shortcuts import redirect
    return redirect('staff:students')

@login_required(login_url='/auth/login/')
def staff_student_detail(request, pk):
    from django.shortcuts import redirect
    return redirect('staff:student_detail', pk=pk)

@login_required(login_url='/auth/login/')
def staff_student_edit(request, pk):
    from django.shortcuts import redirect
    return redirect('staff:student_edit', pk=pk)

@login_required(login_url='/auth/login/')
def staff_courses(request):
    from django.shortcuts import redirect
    return redirect('staff:courses')

@login_required(login_url='/auth/login/')
def staff_course_detail(request, pk):
    from django.shortcuts import redirect
    return redirect('staff:course_detail', pk=pk)

@login_required(login_url='/auth/login/')
def staff_course_units(request, pk):
    from django.shortcuts import redirect
    return redirect('staff:course_units', course_pk=pk)

@login_required(login_url='/auth/login/')
def staff_enrollments(request):
    from django.shortcuts import redirect
    return redirect('staff:enrollments')

@login_required(login_url='/auth/login/')
def staff_academic_periods(request):
    from django.shortcuts import redirect
    return redirect('staff:academic_periods')

@login_required(login_url='/auth/login/')
def staff_finance(request):
    total_billed = sum(i["total"] for i in INVOICES)
    total_paid   = sum(i["paid"]  for i in INVOICES)
    ctx = _base("Finance", "finance")
    ctx.update({"invoices": INVOICES[:5], "payments": PAYMENTS[:5], "total_billed": total_billed, "total_paid": total_paid, "outstanding": total_billed - total_paid, "fee_structures": FEE_STRUCTURES})
    return render(request, "staff/finance.html", ctx)

@login_required(login_url='/auth/login/')
def staff_fee_structures(request):
    ctx = _base("Fee Structures", "finance")
    ctx.update({"structures": FEE_STRUCTURES})
    return render(request, "staff/fee_structures.html", ctx)

@login_required(login_url='/auth/login/')
def staff_invoices(request):
    ctx = _base("Invoices", "finance")
    ctx.update({"invoices": INVOICES, "periods": PERIODS})
    return render(request, "staff/invoices.html", ctx)

@login_required(login_url='/auth/login/')
def staff_invoice_detail(request, invoice_number):
    inv = next((i for i in INVOICES if i["invoice_number"]==invoice_number), INVOICES[0])
    pmts = [p for p in PAYMENTS if p.get("invoice")==invoice_number]
    ctx = _base("Invoice " + invoice_number, "finance")
    ctx.update({"invoice": inv, "payments": pmts})
    return render(request, "staff/invoice_detail.html", ctx)

@login_required(login_url='/auth/login/')
def staff_payments(request):
    ctx = _base("Payments", "finance")
    ctx.update({"payments": PAYMENTS})
    return render(request, "staff/payments.html", ctx)

@login_required(login_url='/auth/login/')
def staff_payment_detail(request, pk):
    pmt = next((p for p in PAYMENTS if p["pk"]==pk), PAYMENTS[0])
    ctx = _base("Payment " + pmt["receipt"], "finance")
    ctx.update({"payment": pmt})
    return render(request, "staff/payment_detail.html", ctx)

@login_required(login_url='/auth/login/')
def staff_results(request):
    ctx = _base("Results", "results")
    ctx.update({"results": RESULTS, "periods": PERIODS})
    return render(request, "staff/results.html", ctx)

@login_required(login_url='/auth/login/')
def staff_results_enter(request):
    ctx = _base("Enter Results", "results")
    ctx.update({"students": STUDENTS, "periods": PERIODS, "courses": COURSES})
    return render(request, "staff/results_enter.html", ctx)

@login_required(login_url='/auth/login/')
def staff_result_detail(request, pk):
    r = next((x for x in RESULTS if x["pk"]==pk), RESULTS[0])
    ctx = _base("Result Detail", "results")
    ctx.update({"result": r})
    return render(request, "staff/result_detail.html", ctx)

@login_required(login_url='/auth/login/')
def staff_content(request):
    ctx = _base("Course Content", "content")
    ctx.update({"items": CONTENT, "courses": COURSES})
    return render(request, "staff/content.html", ctx)

@login_required(login_url='/auth/login/')
def staff_content_create(request):
    ctx = _base("Add Content", "content")
    ctx.update({"courses": COURSES})
    return render(request, "staff/content_create.html", ctx)

@login_required(login_url='/auth/login/')
def staff_users(request):
    ctx = _base("Users", "users")
    ctx.update({"users": USERS})
    return render(request, "staff/users.html", ctx)

@login_required(login_url='/auth/login/')
def staff_staff_list(request):
    from apps.accounts.models import User, AccountStatus
    from django.db.models import Q

    qs = (
        User.objects
        .filter(staffprofile__isnull=False)
        .select_related('staffprofile')
        .prefetch_related('groups')
        .order_by('last_name', 'first_name')
    )

    # Optional search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(staffprofile__staff_number__icontains=q)
            | Q(staffprofile__department__icontains=q)
        )

    ctx = _base("Staff Members", "staff_list")
    ctx.update({
        "staff_members": qs,
        "total": qs.count(),
        "q": q,
        "AccountStatus": AccountStatus,
    })
    return render(request, "staff/staff_list.html", ctx)

@login_required(login_url='/auth/login/')
def staff_groups(request):
    groups = [
        {"pk":1,"name":"Administrator","desc":"Full system access","permissions":47,"members":2},
        {"pk":2,"name":"Registrar","desc":"Student enrollment and records","permissions":18,"members":1},
        {"pk":3,"name":"Finance Officer","desc":"Invoices, payments, and fee structures","permissions":22,"members":1},
        {"pk":4,"name":"Academic Officer","desc":"Results, courses, and academic periods","permissions":24,"members":3},
        {"pk":5,"name":"Lecturer","desc":"Results entry and course content upload","permissions":8,"members":2},
        {"pk":6,"name":"Receptionist","desc":"View-only access to student records","permissions":4,"members":0},
    ]
    ctx = _base("Groups and Roles", "groups")
    ctx.update({"groups": groups})
    return render(request, "staff/groups.html", ctx)

@login_required(login_url='/auth/login/')
def staff_settings(request):
    ctx = _base("System Settings", "settings")
    ctx.update({"settings": {
        "college_name": "Nayolites Compute and Media College",
        "tagline": "Computing. Creating. Leading.",
        "address": "Kimathi Street, Nairobi, Kenya",
        "phone": "+254 700 123 456",
        "email": "info@nayolites.ac.ke",
        "website": "www.nayolites.ac.ke",
        "currency": "KES",
        "currency_symbol": "Ksh",
        "mpesa_paybill": "522500",
        "bank_account": "0190265937383",
    }})
    return render(request, "staff/settings.html", ctx)

@login_required(login_url='/auth/login/')
def staff_audit_log(request):
    ctx = _base("Audit Log", "audit_log")
    ctx.update({"entries": AUDIT_LOG})
    return render(request, "staff/audit_log.html", ctx)


# ============================================================
# Real authorization-backed views — Phase 7
# ============================================================

from django.db.models import Q
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.views import View
from apps.accounts.mixins import StaffRequiredMixin as _StaffMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages as _messages


class GroupListView(_StaffMixin, View):
    """
    GET /staff/groups/ — list all permission groups.
    Replaces prototype staff_groups view.
    Requirements: 8.2, 10.2
    """
    permission_required = 'auth.view_group'

    def get(self, request):
        groups = Group.objects.prefetch_related('permissions', 'user_set').order_by('name')
        group_data = []
        for g in groups:
            group_data.append({
                'group': g,
                'permission_count': g.permissions.count(),
                'member_count': g.user_set.count(),
            })
        return render(request, 'staff/groups/list.html', {
            'page_title': 'Groups & Roles',
            'active_section': 'groups',
            'group_data': group_data,
        })


class GroupDetailView(_StaffMixin, View):
    """
    GET /staff/groups/<pk>/ — group detail with members and permissions.
    Requirements: 8.2, 10.2
    """
    permission_required = 'auth.view_group'

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        members = group.user_set.select_related('staffprofile').order_by('last_name', 'first_name')

        # Organize permissions by content type (app)
        perms_by_app = {}
        for perm in group.permissions.select_related('content_type').order_by(
            'content_type__app_label', 'codename'
        ):
            app = perm.content_type.app_label
            if app not in perms_by_app:
                perms_by_app[app] = []
            perms_by_app[app].append(perm)

        return render(request, 'staff/groups/detail.html', {
            'page_title': f'Group: {group.name}',
            'active_section': 'groups',
            'group': group,
            'members': members,
            'perms_by_app': perms_by_app,
        })


class AuditLogListView(_StaffMixin, View):
    """
    GET /staff/audit-log/ — paginated audit log with filters.
    Replaces prototype staff_audit_log view.
    Requirements: 17.5, 17.6, 17.7
    """
    permission_required = 'core.view_auditlog'

    def get(self, request):
        from apps.core.models import AuditAction, AuditLog
        from django.core.paginator import Paginator

        qs = AuditLog.objects.select_related('actor').order_by('-created_at')

        # Filters
        action_filter = request.GET.get('action', '').strip()
        if action_filter:
            qs = qs.filter(action=action_filter)

        actor_filter = request.GET.get('actor', '').strip()
        if actor_filter:
            qs = qs.filter(
                Q(actor__email__icontains=actor_filter)
                | Q(actor__first_name__icontains=actor_filter)
                | Q(actor__last_name__icontains=actor_filter)
                | Q(description__icontains=actor_filter)
            )

        date_from = request.GET.get('date_from', '').strip()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = request.GET.get('date_to', '').strip()
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        paginator = Paginator(qs, 50)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'staff/audit/list.html', {
            'page_title': 'Audit Log',
            'active_section': 'audit_log',
            'page_obj': page_obj,
            'action_filter': action_filter,
            'actor_filter': actor_filter,
            'date_from': date_from,
            'date_to': date_to,
            'action_choices': AuditAction.choices,
        })


# ============================================================
# AJAX helpers
# ============================================================

@login_required(login_url='/auth/login/')
def ajax_course_units(request):
    """
    GET /staff/ajax/course-units/?course_id=<pk>
    Returns JSON list of active course units for the given course.
    Staff-only (requires login). Used by the Enter Results form to
    populate the unit dropdown dynamically when the course changes.
    """
    from apps.courses.models import CourseUnit

    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    course_id = request.GET.get('course_id', '')
    if not course_id:
        return JsonResponse({'units': []})

    try:
        course_id = int(course_id)
    except (ValueError, TypeError):
        return JsonResponse({'units': []})

    units = (
        CourseUnit.objects
        .filter(course_id=course_id, is_active=True)
        .order_by('code')
        .values('id', 'code', 'name')
    )
    return JsonResponse({'units': list(units)})
