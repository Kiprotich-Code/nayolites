"""
Public website views for the Nayolites Compute and Media College platform.

All views use realistic mock context data representing the college's
actual programme catalogue and institutional information.
"""

from django.shortcuts import render


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

COURSES = [
    {
        'id': 1,
        'slug': 'diploma-computer-science',
        'code': 'DCS',
        'name': 'Diploma in Computer Science',
        'category': 'Computing',
        'duration': '2 Years',
        'intakes': ['January', 'May', 'September'],
        'description': (
            'A comprehensive two-year programme covering programming, '
            'data structures, algorithms, database systems, and software '
            'engineering. Graduates are equipped for roles in software '
            'development, systems analysis, and IT consulting.'
        ),
        'image': 'img/courses/computer-science.jpg',
        'featured': True,
        'units': [
            {'code': 'DCS 101', 'name': 'Introduction to Programming', 'year': 1, 'semester': 1},
            {'code': 'DCS 102', 'name': 'Mathematics for Computing', 'year': 1, 'semester': 1},
            {'code': 'DCS 103', 'name': 'Computer Organization', 'year': 1, 'semester': 1},
            {'code': 'DCS 104', 'name': 'Data Structures and Algorithms', 'year': 1, 'semester': 2},
            {'code': 'DCS 105', 'name': 'Database Management Systems', 'year': 1, 'semester': 2},
            {'code': 'DCS 106', 'name': 'Operating Systems', 'year': 1, 'semester': 2},
            {'code': 'DCS 201', 'name': 'Software Engineering', 'year': 2, 'semester': 1},
            {'code': 'DCS 202', 'name': 'Web Application Development', 'year': 2, 'semester': 1},
            {'code': 'DCS 203', 'name': 'Computer Networks', 'year': 2, 'semester': 1},
            {'code': 'DCS 204', 'name': 'Systems Analysis and Design', 'year': 2, 'semester': 2},
            {'code': 'DCS 205', 'name': 'Cybersecurity Fundamentals', 'year': 2, 'semester': 2},
            {'code': 'DCS 206', 'name': 'Project', 'year': 2, 'semester': 2},
        ],
        'requirements': [
            'Kenya Certificate of Secondary Education (KCSE) Mean Grade C- or above',
            'Credit or above in Mathematics',
            'Credit or above in English',
        ],
        'fees': {
            'registration': 2000,
            'tuition_per_semester': 18000,
            'materials': 3000,
            'examination': 2500,
            'total_per_semester': 25500,
        },
    },
    {
        'id': 2,
        'slug': 'diploma-broadcast-media',
        'code': 'DBM',
        'name': 'Diploma in Broadcast Media',
        'category': 'Media',
        'duration': '2 Years',
        'intakes': ['January', 'September'],
        'description': (
            'An intensive programme in radio, television, and digital '
            'media production. Students develop skills in journalism, '
            'video production, audio engineering, and digital content '
            'creation for broadcast and online platforms.'
        ),
        'image': 'img/courses/broadcast-media.jpg',
        'featured': True,
        'units': [
            {'code': 'DBM 101', 'name': 'Introduction to Mass Communication', 'year': 1, 'semester': 1},
            {'code': 'DBM 102', 'name': 'Radio Production Fundamentals', 'year': 1, 'semester': 1},
            {'code': 'DBM 103', 'name': 'Print and Digital Journalism', 'year': 1, 'semester': 1},
            {'code': 'DBM 104', 'name': 'Television Production', 'year': 1, 'semester': 2},
            {'code': 'DBM 105', 'name': 'Audio Engineering', 'year': 1, 'semester': 2},
            {'code': 'DBM 106', 'name': 'Media Law and Ethics', 'year': 1, 'semester': 2},
            {'code': 'DBM 201', 'name': 'Advanced Video Production', 'year': 2, 'semester': 1},
            {'code': 'DBM 202', 'name': 'Digital Content Strategy', 'year': 2, 'semester': 1},
            {'code': 'DBM 203', 'name': 'News Presentation and Anchoring', 'year': 2, 'semester': 1},
            {'code': 'DBM 204', 'name': 'Social Media Management', 'year': 2, 'semester': 2},
            {'code': 'DBM 205', 'name': 'Media Business and Entrepreneurship', 'year': 2, 'semester': 2},
            {'code': 'DBM 206', 'name': 'Production Project', 'year': 2, 'semester': 2},
        ],
        'requirements': [
            'KCSE Mean Grade C- or above',
            'Credit or above in English',
            'Interest in communication and media',
        ],
        'fees': {
            'registration': 2000,
            'tuition_per_semester': 20000,
            'materials': 4000,
            'examination': 2500,
            'total_per_semester': 28500,
        },
    },
    {
        'id': 3,
        'slug': 'certificate-graphic-design',
        'code': 'CGD',
        'name': 'Certificate in Graphic Design',
        'category': 'Design',
        'duration': '1 Year',
        'intakes': ['January', 'May', 'September'],
        'description': (
            'A practical one-year programme in visual communication, '
            'digital design, branding, and typography. Students master '
            'industry-standard tools including Adobe Creative Suite and '
            'build a professional portfolio.'
        ),
        'image': 'img/courses/graphic-design.jpg',
        'featured': True,
        'units': [
            {'code': 'CGD 101', 'name': 'Principles of Design', 'year': 1, 'semester': 1},
            {'code': 'CGD 102', 'name': 'Digital Illustration', 'year': 1, 'semester': 1},
            {'code': 'CGD 103', 'name': 'Typography and Layout', 'year': 1, 'semester': 1},
            {'code': 'CGD 104', 'name': 'Photo Editing and Retouching', 'year': 1, 'semester': 2},
            {'code': 'CGD 105', 'name': 'Branding and Identity', 'year': 1, 'semester': 2},
            {'code': 'CGD 106', 'name': 'Print Production and Portfolio', 'year': 1, 'semester': 2},
        ],
        'requirements': [
            'KCSE Mean Grade D+ or above',
            'Interest in visual arts or design',
        ],
        'fees': {
            'registration': 2000,
            'tuition_per_semester': 14000,
            'materials': 5000,
            'examination': 2000,
            'total_per_semester': 23000,
        },
    },
    {
        'id': 4,
        'slug': 'certificate-web-development',
        'code': 'CWD',
        'name': 'Certificate in Web Development',
        'category': 'Computing',
        'duration': '1 Year',
        'intakes': ['January', 'May', 'September'],
        'description': (
            'A focused programme covering front-end and back-end web '
            'development. Students learn HTML, CSS, JavaScript, Python, '
            'and Django, completing the course with deployed real-world '
            'projects.'
        ),
        'image': 'img/courses/web-development.jpg',
        'featured': False,
        'units': [
            {'code': 'CWD 101', 'name': 'HTML and CSS Fundamentals', 'year': 1, 'semester': 1},
            {'code': 'CWD 102', 'name': 'JavaScript Programming', 'year': 1, 'semester': 1},
            {'code': 'CWD 103', 'name': 'Responsive Web Design', 'year': 1, 'semester': 1},
            {'code': 'CWD 104', 'name': 'Python for Web Development', 'year': 1, 'semester': 2},
            {'code': 'CWD 105', 'name': 'Django Framework', 'year': 1, 'semester': 2},
            {'code': 'CWD 106', 'name': 'Web Project', 'year': 1, 'semester': 2},
        ],
        'requirements': [
            'KCSE Mean Grade D+ or above',
            'Basic computer literacy',
        ],
        'fees': {
            'registration': 2000,
            'tuition_per_semester': 15000,
            'materials': 3000,
            'examination': 2000,
            'total_per_semester': 22000,
        },
    },
    {
        'id': 5,
        'slug': 'diploma-it-support',
        'code': 'DIT',
        'name': 'Diploma in IT Support',
        'category': 'Computing',
        'duration': '2 Years',
        'intakes': ['January', 'September'],
        'description': (
            'A technical programme preparing students for careers in '
            'IT helpdesk, network administration, and systems support. '
            'Covers hardware, networking, Windows/Linux administration, '
            'and customer service for IT environments.'
        ),
        'image': 'img/courses/it-support.jpg',
        'featured': False,
        'units': [
            {'code': 'DIT 101', 'name': 'Computer Hardware Fundamentals', 'year': 1, 'semester': 1},
            {'code': 'DIT 102', 'name': 'Operating System Administration', 'year': 1, 'semester': 1},
            {'code': 'DIT 103', 'name': 'Networking Basics', 'year': 1, 'semester': 1},
            {'code': 'DIT 104', 'name': 'IT Helpdesk and Customer Support', 'year': 1, 'semester': 2},
            {'code': 'DIT 105', 'name': 'Network Configuration and Security', 'year': 1, 'semester': 2},
            {'code': 'DIT 106', 'name': 'Linux Administration', 'year': 1, 'semester': 2},
            {'code': 'DIT 201', 'name': 'Server Administration', 'year': 2, 'semester': 1},
            {'code': 'DIT 202', 'name': 'Cloud Computing Fundamentals', 'year': 2, 'semester': 1},
            {'code': 'DIT 203', 'name': 'Virtualisation Technologies', 'year': 2, 'semester': 1},
            {'code': 'DIT 204', 'name': 'IT Project Management', 'year': 2, 'semester': 2},
            {'code': 'DIT 205', 'name': 'Cybersecurity and Compliance', 'year': 2, 'semester': 2},
            {'code': 'DIT 206', 'name': 'Attachment and Report', 'year': 2, 'semester': 2},
        ],
        'requirements': [
            'KCSE Mean Grade D+ or above',
            'Basic computer literacy',
        ],
        'fees': {
            'registration': 2000,
            'tuition_per_semester': 16000,
            'materials': 3000,
            'examination': 2500,
            'total_per_semester': 23500,
        },
    },
]

DEPARTMENTS = [
    {
        'name': 'School of Computing',
        'head': 'Mr. James Kamau Njoroge',
        'description': (
            'Delivering computing programmes that prepare graduates for '
            'the modern technology-driven workplace.'
        ),
        'programmes': ['Diploma in Computer Science', 'Diploma in IT Support', 'Certificate in Web Development'],
    },
    {
        'name': 'School of Media and Communication',
        'head': 'Ms. Grace Nyambura Mwangi',
        'description': (
            'Training the next generation of media professionals in '
            'broadcast, digital, and print communication.'
        ),
        'programmes': ['Diploma in Broadcast Media'],
    },
    {
        'name': 'School of Creative Arts',
        'head': 'Mr. Peter Otieno Ochieng',
        'description': (
            'Nurturing creative talent through design, visual '
            'communication, and digital arts programmes.'
        ),
        'programmes': ['Certificate in Graphic Design'],
    },
]


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def public_home(request):
    """
    College homepage with featured courses pulled from the database.
    Falls back to mock data if the Course table is empty (fresh install).
    """
    from apps.courses.models import Course as CourseModel

    db_courses = list(CourseModel.objects.filter(is_active=True).order_by('name')[:6])

    if db_courses:
        # Shape DB records to match the template's expected keys
        featured_courses = [
            {
                'id': c.pk,
                'slug': c.slug,
                'code': c.code,
                'name': c.name,
                'description': c.description,
                'duration': c.duration,
                'unit_count': c.unit_count,
                'from_db': True,
            }
            for c in db_courses
        ]
        total_courses = CourseModel.objects.filter(is_active=True).count()
    else:
        # Fallback: use mock data so the page never looks empty
        featured_courses = [c for c in COURSES if c.get('featured')]
        total_courses = len(COURSES)

    context = {
        'page_title': 'Nayolites Compute and Media College',
        'featured_courses': featured_courses,
        'total_courses': total_courses,
        'total_students': 847,
        'years_established': 12,
        'departments': DEPARTMENTS,
        'hero': {
            'headline': 'Computing. Creating. Leading.',
            'subheadline': (
                'Join a community of learners building careers in '
                'technology, media, and design.'
            ),
            'cta_primary': {'label': 'View Programmes', 'url': '/courses/'},
            'cta_secondary': {'label': 'Apply Now', 'url': '/admissions/'},
        },
        'next_intake': 'September 2026',
        'admission_open': True,
    }
    return render(request, 'public/home.html', context)


def public_about(request):
    """
    About the college: mission, vision, history, departments, and leadership.
    """
    context = {
        'page_title': 'About Us',
        'mission': (
            'To provide quality, relevant, and accessible technical and '
            'media education that equips students with the skills and '
            'character to succeed in a competitive global economy.'
        ),
        'vision': (
            'To be East Africa\'s most respected college for computing '
            'and media education, producing graduates who lead and '
            'innovate in their fields.'
        ),
        'core_values': [
            {'value': 'Excellence', 'description': 'We hold every student, lecturer, and process to high standards.'},
            {'value': 'Integrity', 'description': 'We are honest, transparent, and accountable in everything we do.'},
            {'value': 'Relevance', 'description': 'Our programmes respond to real industry needs, not tradition alone.'},
            {'value': 'Accessibility', 'description': 'We believe quality education should be within reach.'},
            {'value': 'Innovation', 'description': 'We encourage creative thinking and practical problem-solving.'},
        ],
        'history': (
            'Nayolites Compute and Media College was established in 2013 '
            'on Kimathi Street in the heart of Nairobi. Founded with a '
            'single computing programme and thirty students, the college '
            'has grown to serve over eight hundred students across five '
            'programmes in computing, media, and design. The college is '
            'registered with the Technical and Vocational Education and '
            'Training Authority (TVETA) and maintains strong links with '
            'the Kenya ICT Authority and media industry partners.'
        ),
        'departments': DEPARTMENTS,
        'leadership': [
            {
                'name': 'Mr. Solomon Waweru Kimani',
                'title': 'Principal',
                'bio': (
                    'Mr. Kimani holds an MSc in Computer Science from the '
                    'University of Nairobi and has over 20 years of '
                    'experience in technical education.'
                ),
            },
            {
                'name': 'Mrs. Florence Achieng Oduor',
                'title': 'Deputy Principal, Academics',
                'bio': (
                    'Mrs. Oduor oversees academic quality and curriculum '
                    'development. She holds an MA in Education Management '
                    'from Kenyatta University.'
                ),
            },
            {
                'name': 'Mr. Dennis Mwangi Kariuki',
                'title': 'Deputy Principal, Finance and Administration',
                'bio': (
                    'Mr. Kariuki manages institutional finances and operations. '
                    'He holds a CPA(K) and a BCom from the University of Nairobi.'
                ),
            },
        ],
        'accreditations': [
            'Technical and Vocational Education and Training Authority (TVETA)',
            'Kenya National Qualifications Authority (KNQA)',
        ],
    }
    return render(request, 'public/about.html', context)


def public_courses(request):
    """
    Full programme catalogue.
    """
    # Group courses by category
    categories = {}
    for course in COURSES:
        cat = course['category']
        categories.setdefault(cat, []).append(course)

    context = {
        'page_title': 'Our Programmes',
        'courses': COURSES,
        'categories': categories,
        'total': len(COURSES),
    }
    return render(request, 'public/courses.html', context)


def public_course_detail(request, slug):
    """
    Single course detail page with units, requirements, and fees.
    """
    course = next((c for c in COURSES if c['slug'] == slug), None)

    if course is None:
        from django.http import Http404
        raise Http404('Programme not found.')

    # Group units by year and semester
    by_year = {}
    for unit in course.get('units', []):
        year_key = f"Year {unit['year']}"
        sem_key = f"Semester {unit['semester']}"
        by_year.setdefault(year_key, {}).setdefault(sem_key, []).append(unit)

    # Find related courses (same category, excluding this one)
    related = [c for c in COURSES if c['category'] == course['category'] and c['slug'] != slug][:3]

    context = {
        'page_title': course['name'],
        'course': course,
        'units_by_year': by_year,
        'related_courses': related,
    }
    return render(request, 'public/course_detail.html', context)


def public_admissions(request):
    """
    Admissions information: requirements, process, and intake dates.
    """
    context = {
        'page_title': 'Admissions',
        'intro': (
            'Nayolites Compute and Media College welcomes applications '
            'from motivated students ready to build careers in technology, '
            'media, and design. We offer three intakes per year for most '
            'programmes.'
        ),
        'intakes': [
            {
                'period': 'January 2026',
                'application_deadline': '15 December 2025',
                'classes_begin': '13 January 2026',
                'status': 'upcoming',
            },
            {
                'period': 'September 2025',
                'application_deadline': '22 August 2025',
                'classes_begin': '8 September 2025',
                'status': 'open',
            },
            {
                'period': 'May 2025',
                'application_deadline': '25 April 2025',
                'classes_begin': '5 May 2025',
                'status': 'closed',
            },
        ],
        'general_requirements': [
            'Kenya Certificate of Secondary Education (KCSE) certificate or equivalent',
            'National Identity Card or Birth Certificate',
            'Passport-size photograph (two copies)',
            'Completed application form',
            'Application fee of Ksh 500 (non-refundable)',
        ],
        'process_steps': [
            {
                'step': 1,
                'title': 'Choose Your Programme',
                'description': 'Review our programme catalogue and identify the course that aligns with your goals.',
            },
            {
                'step': 2,
                'title': 'Confirm Eligibility',
                'description': 'Check the specific entry requirements for your chosen programme.',
            },
            {
                'step': 3,
                'title': 'Submit Application',
                'description': 'Visit the admissions office with your documents or contact us to begin the process.',
            },
            {
                'step': 4,
                'title': 'Admission Letter',
                'description': 'Successful applicants receive an admission letter and reporting instructions.',
            },
            {
                'step': 5,
                'title': 'Enrol and Pay',
                'description': 'Report on the specified date, complete enrollment, and pay the required fees.',
            },
        ],
        'courses': COURSES,
        'contact': {
            'office': 'Admissions Office, Ground Floor',
            'phone': '+254 700 123 456',
            'email': 'admissions@nayolites.ac.ke',
            'hours': 'Monday–Friday, 8:00 AM – 5:00 PM',
        },
    }
    return render(request, 'public/admissions.html', context)


def public_fees(request):
    """
    Fee structures per programme.
    """
    fee_table = []
    for course in COURSES:
        f = course.get('fees', {})
        fee_table.append({
            'course_name': course['name'],
            'code': course['code'],
            'duration': course['duration'],
            'registration': f.get('registration', 0),
            'tuition_per_semester': f.get('tuition_per_semester', 0),
            'materials': f.get('materials', 0),
            'examination': f.get('examination', 0),
            'total_per_semester': f.get('total_per_semester', 0),
        })

    context = {
        'page_title': 'Fees and Financing',
        'intro': (
            'The following fee structures apply to the current academic year. '
            'Fees are payable per semester. Partial payment arrangements may '
            'be discussed with the Finance Office.'
        ),
        'fee_table': fee_table,
        'notes': [
            'Registration fee is a one-time charge payable on first enrollment.',
            'Materials fees vary by programme based on practical requirements.',
            'Examination fees cover internal and external assessments.',
            'Fees are reviewed annually and are subject to change with notice.',
            'Government bursary and HELB loan applications are supported.',
        ],
        'payment_methods': [
            {'method': 'M-Pesa', 'details': 'Paybill: 522500, Account: Your Admission Number'},
            {'method': 'Bank Transfer', 'details': 'Equity Bank, A/C: 0190265937383, Branch: Kimathi Street'},
            {'method': 'Cash', 'details': 'Finance Office, Ground Floor, 8:00 AM – 4:30 PM'},
        ],
        'finance_contact': {
            'phone': '+254 700 123 456',
            'email': 'finance@nayolites.ac.ke',
        },
    }
    return render(request, 'public/fees.html', context)


def public_contact(request):
    """
    Contact page with address, phone, email, and map placeholder.
    """
    context = {
        'page_title': 'Contact Us',
        'address': {
            'street': 'Kimathi Street',
            'building': 'Nayolites House, 3rd Floor',
            'city': 'Nairobi',
            'country': 'Kenya',
            'po_box': 'P.O. Box 47892 – 00100, Nairobi',
        },
        'contacts': [
            {'label': 'General Enquiries', 'phone': '+254 700 123 456', 'email': 'info@nayolites.ac.ke'},
            {'label': 'Admissions', 'phone': '+254 700 123 457', 'email': 'admissions@nayolites.ac.ke'},
            {'label': 'Finance Office', 'phone': '+254 700 123 458', 'email': 'finance@nayolites.ac.ke'},
            {'label': 'Academic Office', 'phone': '+254 700 123 459', 'email': 'academics@nayolites.ac.ke'},
        ],
        'hours': [
            {'day': 'Monday – Friday', 'time': '8:00 AM – 5:00 PM'},
            {'day': 'Saturday', 'time': '9:00 AM – 1:00 PM'},
            {'day': 'Sunday & Public Holidays', 'time': 'Closed'},
        ],
        # Approximate coordinates for Kimathi Street, Nairobi
        'map': {
            'latitude': -1.2833,
            'longitude': 36.8172,
            'zoom': 16,
            'label': 'Nayolites Compute and Media College',
        },
        'social': [
            {'platform': 'Facebook', 'url': 'https://facebook.com/nayolites', 'handle': '@nayolites'},
            {'platform': 'Twitter / X', 'url': 'https://twitter.com/nayolites', 'handle': '@nayolites'},
            {'platform': 'Instagram', 'url': 'https://instagram.com/nayolites', 'handle': '@nayolites'},
            {'platform': 'LinkedIn', 'url': 'https://linkedin.com/school/nayolites', 'handle': 'Nayolites College'},
        ],
    }
    return render(request, 'public/contact.html', context)
