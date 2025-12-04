# petapp/views_adoption_application.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import (
    AdoptionPet,
    AdoptionApplication,
    ApplicationMessage,
    AdoptionTransferRequest,
    ApplicantProfile,
    Notification
)

# ============================================
# 📝 B飼主功能 - 申請領養
# ============================================

@login_required
def apply_for_adoption(request, pet_id):
    """
    申請領養寵物
    B飼主填寫詳細申請表單
    """
    pet = get_object_or_404(AdoptionPet, id=pet_id, is_publish=True, is_adopted=False)

    # 檢查是否為寵物主人（不能申請自己的寵物）
    if pet.owner == request.user:
        messages.error(request, '您不能申請領養自己的寵物')
        return redirect('adoption_petDetail', adoption_id=pet_id)

    # 檢查是否已經申請過
    existing_application = AdoptionApplication.objects.filter(
        pet=pet,
        applicant=request.user,
        status__in=['pending', 'reviewing']
    ).first()

    if existing_application:
        messages.warning(request, '您已經申請過這隻寵物了，請等待審核')
        return redirect('adoption_application_detail', application_id=existing_application.id)

    if request.method == 'POST':
        try:
            # 建立申請
            application = AdoptionApplication.objects.create(
                pet=pet,
                applicant=request.user,
                owner=pet.owner,

                # 聯絡資訊
                contact_phone=request.POST.get('contact_phone'),
                contact_line=request.POST.get('contact_line', ''),
                contact_email=request.POST.get('contact_email'),

                # 背景資料
                age=request.POST.get('age'),
                occupation=request.POST.get('occupation'),
                residence_type=request.POST.get('residence_type'),
                residence_ownership=request.POST.get('residence_ownership'),
                has_yard=request.POST.get('has_yard') == 'on',
                yard_size=request.POST.get('yard_size', ''),

                # 家庭狀況
                family_members=request.POST.get('family_members'),
                family_agree=request.POST.get('family_agree') == 'on',
                has_children=request.POST.get('has_children') == 'on',
                children_age=request.POST.get('children_age', ''),

                # 飼養經驗
                has_pet_experience=request.POST.get('has_pet_experience') == 'on',
                pet_experience_detail=request.POST.get('pet_experience_detail', ''),
                current_pets=request.POST.get('current_pets', ''),
                pets_count=request.POST.get('pets_count', 0),

                # 經濟狀況
                monthly_income_range=request.POST.get('monthly_income_range'),
                can_afford_medical=request.POST.get('can_afford_medical') == 'on',

                # 領養動機
                adoption_reason=request.POST.get('adoption_reason'),
                how_to_care=request.POST.get('how_to_care'),
                daily_time_for_pet=request.POST.get('daily_time_for_pet'),
                emergency_plan=request.POST.get('emergency_plan', ''),

                # 其他
                additional_message=request.POST.get('additional_message', ''),
                is_willing_home_visit=request.POST.get('is_willing_home_visit') == 'on',

                status='pending'
            )

            messages.success(request, f'已成功送出領養申請！請等待 {pet.owner.username} 的審核')

            # 發送通知給原飼主
            Notification.objects.create(
                recipient=pet.owner,
                sender=request.user,
                notification_type='adoption_application_new',
                title='收到新的領養申請',
                message=f'{request.user.username} 申請領養您的寵物「{pet.name}」',
                target_url=f'/adoption/applications/{application.id}/'
            )

            return redirect('adoption_application_detail', application_id=application.id)

        except Exception as e:
            messages.error(request, f'申請失敗：{str(e)}')
            return redirect('adoption_petDetail', adoption_id=pet_id)

    # GET 請求：顯示申請表單
    # 嘗試載入已儲存的申請人資料
    try:
        profile = ApplicantProfile.objects.get(user=request.user)
    except ApplicantProfile.DoesNotExist:
        profile = None

    return render(request, 'adoption/application_form.html', {
        'pet': pet,
        'profile': profile  # 傳遞已儲存的資料到模板
    })


@login_required
def my_adoption_applications(request):
    """
    我的領養申請列表
    B飼主查看自己提出的所有申請
    """
    applications = AdoptionApplication.objects.filter(
        applicant=request.user
    ).select_related('pet', 'owner').order_by('-created_at')

    # 標記已讀
    applications.filter(applicant_has_seen_response=False, status__in=['accepted', 'rejected']).update(
        applicant_has_seen_response=True
    )

    return render(request, 'adoption/my_applications.html', {
        'applications': applications
    })


@login_required
def cancel_adoption_application(request, application_id):
    """
    取消申請
    B飼主取消自己的申請
    """
    application = get_object_or_404(
        AdoptionApplication,
        id=application_id,
        applicant=request.user
    )

    # 如果申請已經被取消，直接重定向到詳情頁面
    if application.status == 'cancelled':
        messages.info(request, '此申請已經被取消')
        return redirect('adoption_application_detail', application_id=application_id)

    # 檢查是否可以取消（pending 或 reviewing 狀態）
    if application.status not in ['pending', 'reviewing']:
        messages.error(request, '此申請已無法取消')
        return redirect('adoption_application_detail', application_id=application_id)

    if request.method == 'POST':
        application.status = 'cancelled'
        application.updated_at = timezone.now()
        application.save()

        messages.success(request, '已取消申請')

        # 通知原飼主
        Notification.objects.create(
            recipient=application.owner,
            sender=request.user,
            notification_type='adoption_application_cancelled',
            title='領養申請已取消',
            message=f'{request.user.username} 取消了對「{application.pet.name}」的領養申請',
            target_url=f'/adoption/applications/{application.id}/'
        )

        return redirect('my_adoption_applications')

    return render(request, 'adoption/cancel_application_confirm.html', {
        'application': application
    })


# ============================================
# 👀 A飼主功能 - 審核申請
# ============================================

@login_required
def owner_adoption_applications(request, pet_id=None):
    """
    原飼主查看收到的所有申請
    可以篩選特定寵物的申請
    """
    # 獲取篩選參數
    status_filter = request.GET.get('status', '')
    pet_filter = request.GET.get('pet', '')
    search_query = request.GET.get('search', '')

    # 詳細篩選參數
    residence_type_filter = request.GET.get('residence_type', '')
    residence_ownership_filter = request.GET.get('residence_ownership', '')
    has_pet_experience_filter = request.GET.get('has_pet_experience', '')
    age_min = request.GET.get('age_min', '')
    age_max = request.GET.get('age_max', '')
    has_yard_filter = request.GET.get('has_yard', '')
    can_afford_medical_filter = request.GET.get('can_afford_medical', '')
    is_willing_home_visit_filter = request.GET.get('is_willing_home_visit', '')

    if pet_id:
        pet = get_object_or_404(AdoptionPet, id=pet_id, owner=request.user)
        applications = AdoptionApplication.objects.filter(
            pet=pet
        ).select_related('applicant', 'pet').order_by('-created_at')

        context = {
            'pet': pet,
            'applications': applications
        }
    else:
        # 查看所有送養寵物的申請
        applications = AdoptionApplication.objects.filter(
            owner=request.user
        ).select_related('applicant', 'pet')

        # 按狀態篩選
        if status_filter:
            applications = applications.filter(status=status_filter)

        # 按寵物篩選
        if pet_filter:
            applications = applications.filter(pet_id=pet_filter)

        # 搜尋功能（搜尋申請人名稱）
        if search_query:
            applications = applications.filter(applicant__username__icontains=search_query)

        # 詳細篩選
        # 住宅類型篩選
        if residence_type_filter:
            applications = applications.filter(residence_type=residence_type_filter)

        # 房屋所有權篩選
        if residence_ownership_filter:
            applications = applications.filter(residence_ownership=residence_ownership_filter)

        # 飼養經驗篩選
        if has_pet_experience_filter:
            if has_pet_experience_filter == 'yes':
                applications = applications.filter(has_pet_experience=True)
            elif has_pet_experience_filter == 'no':
                applications = applications.filter(has_pet_experience=False)

        # 年齡範圍篩選
        if age_min:
            try:
                applications = applications.filter(age__gte=int(age_min))
            except ValueError:
                pass

        if age_max:
            try:
                applications = applications.filter(age__lte=int(age_max))
            except ValueError:
                pass

        # 有無院子篩選
        if has_yard_filter:
            if has_yard_filter == 'yes':
                applications = applications.filter(has_yard=True)
            elif has_yard_filter == 'no':
                applications = applications.filter(has_yard=False)

        # 能否負擔醫療費用篩選
        if can_afford_medical_filter:
            if can_afford_medical_filter == 'yes':
                applications = applications.filter(can_afford_medical=True)
            elif can_afford_medical_filter == 'no':
                applications = applications.filter(can_afford_medical=False)

        # 願意接受家訪篩選
        if is_willing_home_visit_filter:
            if is_willing_home_visit_filter == 'yes':
                applications = applications.filter(is_willing_home_visit=True)
            elif is_willing_home_visit_filter == 'no':
                applications = applications.filter(is_willing_home_visit=False)

        # 排序
        applications = applications.order_by('-created_at')

        # 統計資料（使用未篩選的全部申請）
        all_applications = AdoptionApplication.objects.filter(owner=request.user)
        stats = {
            'total': all_applications.count(),
            'pending': all_applications.filter(status='pending').count(),
            'reviewing': all_applications.filter(status='reviewing').count(),
            'accepted': all_applications.filter(status='accepted').count(),
            'rejected': all_applications.filter(status='rejected').count(),
            'cancelled': all_applications.filter(status='cancelled').count(),
        }

        # 獲取使用者的所有送養寵物（用於篩選下拉選單）
        user_pets = AdoptionPet.objects.filter(owner=request.user)

        context = {
            'applications': applications,
            'stats': stats,
            'user_pets': user_pets,
            'status_filter': status_filter,
            'pet_filter': pet_filter,
            'search_query': search_query,
            # 詳細篩選參數
            'residence_type_filter': residence_type_filter,
            'residence_ownership_filter': residence_ownership_filter,
            'has_pet_experience_filter': has_pet_experience_filter,
            'age_min': age_min,
            'age_max': age_max,
            'has_yard_filter': has_yard_filter,
            'can_afford_medical_filter': can_afford_medical_filter,
            'is_willing_home_visit_filter': is_willing_home_visit_filter,
        }

    # 標記已讀
    applications.filter(owner_has_seen=False).update(owner_has_seen=True)

    return render(request, 'adoption/owner_applications.html', context)


@login_required
def adoption_application_detail(request, application_id):
    """
    查看申請詳情
    A飼主和B飼主都能查看
    """
    application = get_object_or_404(AdoptionApplication, id=application_id)

    # 權限檢查：只有申請人或原飼主可以查看
    if request.user not in [application.applicant, application.owner]:
        messages.error(request, '您沒有權限查看此申請')
        return redirect('adoption')

    # 獲取訊息記錄
    messages_list = ApplicationMessage.objects.filter(
        application=application
    ).select_related('sender', 'recipient').order_by('created_at')

    # 標記已讀
    if request.user == application.owner and not application.owner_has_seen:
        application.owner_has_seen = True
        application.save(update_fields=['owner_has_seen'])
    elif request.user == application.applicant and not application.applicant_has_seen_response:
        application.applicant_has_seen_response = True
        application.save(update_fields=['applicant_has_seen_response'])

    return render(request, 'adoption/application_detail.html', {
        'application': application,
        'messages': messages_list,
        'is_owner': request.user == application.owner,
        'is_applicant': request.user == application.applicant
    })


@login_required
def accept_adoption_application(request, application_id):
    """
    接受申請
    A飼主接受某個申請，並自動拒絕其他申請
    """
    application = get_object_or_404(
        AdoptionApplication,
        id=application_id,
        owner=request.user
    )

    # 如果申請已經被接受，直接重定向到詳情頁面
    if application.status == 'accepted':
        messages.info(request, '此申請已經被接受')
        return redirect('adoption_application_detail', application_id=application_id)

    # 檢查是否可以接受（pending 或 reviewing 狀態，且寵物未被領養）
    if not application.can_be_accepted:
        messages.error(request, '此申請無法接受')
        return redirect('adoption_application_detail', application_id=application_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. 標記此申請為已接受
                application.status = 'accepted'
                application.reviewed_at = timezone.now()
                application.owner_notes = request.POST.get('owner_notes', '')
                application.save()

                # 2. 拒絕同一寵物的其他待審申請
                other_applications = AdoptionApplication.objects.filter(
                    pet=application.pet,
                    status__in=['pending', 'reviewing']
                ).exclude(id=application_id)

                for other_app in other_applications:
                    other_app.status = 'rejected'
                    other_app.reviewed_at = timezone.now()
                    other_app.reject_reason = '此寵物已被其他飼主領養'
                    other_app.save()

                    # 通知其他申請者
                    Notification.objects.create(
                        recipient=other_app.applicant,
                        sender=request.user,
                        notification_type='adoption_application_rejected',
                        title='領養申請已被拒絕',
                        message=f'您對「{application.pet.name}」的領養申請已被拒絕：{other_app.reject_reason}',
                        target_url=f'/adoption/applications/{other_app.id}/'
                    )

                # 3. 標記寵物為已領養
                pet = application.pet
                pet.is_adopted = True
                pet.save()

                # 4. 建立轉交請求（可選）
                transfer_request = AdoptionTransferRequest.objects.create(
                    adoption=pet,
                    from_owner=request.user,
                    to_email=application.contact_email,
                    to_phone=application.contact_phone,
                    to_user=application.applicant,
                    transfer_note=f'接受領養申請 #{application.id}',
                    status='pending'
                )

                messages.success(request, f'已接受 {application.applicant.username} 的申請！已發送轉交請求給申請人')

                # 通知申請者
                Notification.objects.create(
                    recipient=application.applicant,
                    sender=request.user,
                    notification_type='adoption_application_accepted',
                    title='領養申請已接受',
                    message=f'恭喜！您對「{application.pet.name}」的領養申請已被接受，請至轉交請求頁面確認轉交',
                    target_url=f'/adoption/transfer/confirm/{transfer_request.id}/'
                )

                return redirect('adoption_application_detail', application_id=application.id)

        except Exception as e:
            messages.error(request, f'接受申請失敗：{str(e)}')
            return redirect('adoption_application_detail', application_id=application_id)

    return render(request, 'adoption/accept_application_confirm.html', {
        'application': application
    })


@login_required
def reject_adoption_application(request, application_id):
    """
    拒絕申請
    A飼主拒絕某個申請並說明原因
    """
    application = get_object_or_404(
        AdoptionApplication,
        id=application_id,
        owner=request.user
    )

    # 如果申請已經被拒絕，直接重定向到詳情頁面
    if application.status == 'rejected':
        messages.info(request, '此申請已經被拒絕')
        return redirect('adoption_application_detail', application_id=application_id)

    # 檢查是否可以拒絕（pending 或 reviewing 狀態）
    if not application.can_be_rejected:
        messages.error(request, '此申請無法拒絕')
        return redirect('adoption_application_detail', application_id=application_id)

    if request.method == 'POST':
        application.status = 'rejected'
        application.reviewed_at = timezone.now()
        application.reject_reason = request.POST.get('reject_reason', '')
        application.owner_notes = request.POST.get('owner_notes', '')
        application.save()

        messages.success(request, '已拒絕此申請')

        # 通知申請者
        Notification.objects.create(
            recipient=application.applicant,
            sender=request.user,
            notification_type='adoption_application_rejected',
            title='領養申請已被拒絕',
            message=f'您對「{application.pet.name}」的領養申請已被拒絕',
            target_url=f'/adoption/applications/{application.id}/'
        )

        return redirect('owner_adoption_applications')

    return render(request, 'adoption/reject_application_confirm.html', {
        'application': application
    })


@login_required
def mark_application_reviewing(request, application_id):
    """
    標記申請為「審核中」
    A飼主表示正在認真考慮這個申請
    """
    application = get_object_or_404(
        AdoptionApplication,
        id=application_id,
        owner=request.user,
        status='pending'
    )

    application.status = 'reviewing'
    application.save()

    messages.success(request, '已標記為審核中')

    # TODO: 通知申請者
    # create_notification(application.applicant, '您的申請正在審核中')

    return redirect('adoption_application_detail', application_id=application_id)


# ============================================
# 💬 訊息系統
# ============================================

@login_required
def send_application_message(request, application_id):
    """
    發送訊息
    申請人和原飼主可以互相溝通
    """
    application = get_object_or_404(AdoptionApplication, id=application_id)

    # 權限檢查
    if request.user not in [application.applicant, application.owner]:
        messages.error(request, '您沒有權限發送訊息')
        return redirect('adoption')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()

        if not message_text:
            messages.error(request, '訊息不能為空')
            return redirect('adoption_application_detail', application_id=application_id)

        # 確定收件人
        recipient = application.owner if request.user == application.applicant else application.applicant

        # 建立訊息
        ApplicationMessage.objects.create(
            application=application,
            sender=request.user,
            recipient=recipient,
            message=message_text
        )

        messages.success(request, '訊息已發送')

        # TODO: 通知收件人
        # create_notification(recipient, f'{request.user.username} 發送了一則訊息')

        return redirect('adoption_application_detail', application_id=application_id)

    return redirect('adoption_application_detail', application_id=application_id)


# ============================================
# ⚙️ 申請人資料設定
# ============================================

@login_required
def applicant_profile_settings(request):
    """
    申請人資料設定
    讓使用者預先儲存常用的申請資料
    """
    # 取得或建立申請人資料
    profile, created = ApplicantProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        try:
            # 更新聯絡資訊
            profile.contact_phone = request.POST.get('contact_phone', '')
            profile.contact_line = request.POST.get('contact_line', '')
            profile.contact_email = request.POST.get('contact_email', '')

            # 更新背景資料
            age = request.POST.get('age', '')
            profile.age = int(age) if age else None
            profile.occupation = request.POST.get('occupation', '')
            profile.residence_type = request.POST.get('residence_type', '')
            profile.residence_ownership = request.POST.get('residence_ownership', '')
            profile.has_yard = request.POST.get('has_yard') == 'on'
            profile.yard_size = request.POST.get('yard_size', '')

            # 更新家庭狀況
            family_members = request.POST.get('family_members', '')
            profile.family_members = int(family_members) if family_members else None
            profile.family_agree = request.POST.get('family_agree') == 'on'
            profile.has_children = request.POST.get('has_children') == 'on'
            profile.children_age = request.POST.get('children_age', '')

            # 更新飼養經驗
            profile.has_pet_experience = request.POST.get('has_pet_experience') == 'on'
            profile.pet_experience_detail = request.POST.get('pet_experience_detail', '')
            profile.current_pets = request.POST.get('current_pets', '')
            pets_count = request.POST.get('pets_count', '0')
            profile.pets_count = int(pets_count) if pets_count else 0

            # 更新經濟狀況
            profile.monthly_income_range = request.POST.get('monthly_income_range', '')
            profile.can_afford_medical = request.POST.get('can_afford_medical') == 'on'

            # 更新其他資訊
            profile.daily_time_for_pet = request.POST.get('daily_time_for_pet', '')
            profile.emergency_plan = request.POST.get('emergency_plan', '')
            profile.is_willing_home_visit = request.POST.get('is_willing_home_visit') == 'on'

            profile.save()

            messages.success(request, '申請資料已儲存！未來申請領養時會自動帶入這些資料')
            return redirect('applicant_profile_settings')

        except Exception as e:
            messages.error(request, f'儲存失敗：{str(e)}')

    # 獲取用戶的註冊電話號碼
    user_phone = ''
    try:
        if hasattr(request.user, 'profile') and request.user.profile.phone_number:
            user_phone = request.user.profile.phone_number
    except:
        pass

    return render(request, 'adoption/applicant_profile_settings.html', {
        'profile': profile,
        'user_phone': user_phone
    })
