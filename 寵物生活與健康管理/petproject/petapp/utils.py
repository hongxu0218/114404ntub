
from datetime import datetime, time, timedelta, date
from django.utils import timezone
from calendar import monthrange
from django.utils.timezone import localtime
from django.db.models import Q, Count, Avg, Max
from .models import DailyRecord, VetAppointment, Pet, VaccineRecord, DewormRecord, MedicalRecord, PetTag
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# （體溫）共用程式
def get_temperature_data(pet, year, month):
    """
    根據寵物與月份，取得該月所有有效體溫紀錄，並整理成趨勢圖可用格式。
    """
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    records = []
    for rec in raw_records:
        try:
            temp_value = float(rec.content)
        except ValueError:
            continue
        records.append({
            'id': rec.id,
            'date': rec.date.strftime('%Y-%m-%d'),
            'datetime': rec.date.strftime('%Y-%m-%d'),
            'recorded_date': rec.date.strftime('%Y-%m-%d'),
            'submitted_at': localtime(rec.created_at).strftime('%H:%M'),
            'temperature': temp_value,
            'raw_content': rec.content,
        })
    return records

# （體重）共用程式
def get_weight_data(pet, year, month):
    """
    根據寵物與月份，取得該月所有有效體溫紀錄，並整理成趨勢圖可用格式。
    """
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    raw_records = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__range=(start_date, end_date)
    ).order_by('date', 'created_at')

    records = []
    for rec in raw_records:
        try:
            weight_value = float(rec.content)
        except ValueError:
            continue
        records.append({
            'id': rec.id,
            'date': rec.date.strftime('%Y-%m-%d'),
            'datetime': rec.date.strftime('%Y-%m-%d'),
            'recorded_date': rec.date.strftime('%Y-%m-%d'),
            'submitted_at': localtime(rec.created_at).strftime('%H:%M'),
            'weight': weight_value,
            'raw_content': rec.content,
        })
    return records

def time_overlap(start1, end1, start2, end2):
    """
    檢查兩個時間段是否重疊
    
    Args:
        start1, end1: 第一個時間段的開始和結束時間
        start2, end2: 第二個時間段的開始和結束時間
    
    Returns:
        bool: 如果有重疊返回 True，否則返回 False
    """
    return start1 < end2 and start2 < end1

def check_time_period_conflicts(periods):
    """
    檢查多個時間段是否有衝突
    
    Args:
        periods: 時間段列表，每個元素包含 start_time 和 end_time
    
    Returns:
        list: 衝突的時間段組合
    """
    conflicts = []
    
    for i, period1 in enumerate(periods):
        for j, period2 in enumerate(periods[i+1:], i+1):
            if time_overlap(period1['start_time'], period1['end_time'],
                          period2['start_time'], period2['end_time']):
                conflicts.append({
                    'period1': period1,
                    'period2': period2,
                    'index1': i,
                    'index2': j
                })
    
    return conflicts

def calculate_schedule_coverage(schedules, target_hours_per_day=8):
    """
    計算排班覆蓋率
    
    Args:
        schedules: VetSchedule 查詢集或列表
        target_hours_per_day: 每日目標工作時數
    
    Returns:
        dict: 包含覆蓋率統計資料
    """
    daily_coverage = {i: 0 for i in range(7)}  # 週一到週日
    
    for schedule in schedules:
        if schedule.is_active:
            duration = schedule.duration_hours
            daily_coverage[schedule.weekday] += duration
    
    total_coverage = sum(daily_coverage.values())
    total_target = target_hours_per_day * 7
    coverage_percentage = (total_coverage / total_target * 100) if total_target > 0 else 0
    
    return {
        'daily_coverage': daily_coverage,
        'total_coverage': total_coverage,
        'total_target': total_target,
        'coverage_percentage': round(coverage_percentage, 2),
        'under_coverage_days': [day for day, hours in daily_coverage.items() if hours < target_hours_per_day]
    }

def get_available_time_slots(doctor, date, duration_minutes=30):
    """
    取得指定醫師和日期的可用時間段
    
    Args:
        doctor: VetDoctor 實例
        date: 日期對象
        duration_minutes: 時間段長度（分鐘）
    
    Returns:
        list: 可用時間段列表
    """
    from .models import VetSchedule, VetAppointment
    
    weekday = date.weekday()
    schedules = VetSchedule.objects.filter(
        doctor=doctor,
        weekday=weekday,
        is_active=True
    ).order_by('start_time')
    
    available_slots = []
    
    for schedule in schedules:
        current_time = datetime.combine(date, schedule.start_time)
        end_time = datetime.combine(date, schedule.end_time)
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_start = current_time.time()
            slot_end = (current_time + timedelta(minutes=duration_minutes)).time()
            
            # 檢查是否已有預約
            existing_appointment = VetAppointment.objects.filter(
                slot__doctor=doctor,
                slot__date=date,
                slot__start_time=slot_start,
                status__in=['pending', 'confirmed']
            ).exists()
            
            if not existing_appointment:
                available_slots.append({
                    'start_time': slot_start,
                    'end_time': slot_end,
                    'display': f"{slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}"
                })
            
            current_time += timedelta(minutes=duration_minutes)
    
    return available_slots

def detect_schedule_conflicts_for_clinic(clinic, week_start=None):
    """
    檢測診所的排班衝突
    
    Args:
        clinic: VetClinic 實例
        week_start: 週開始日期，預設為本週
    
    Returns:
        list: 衝突列表
    """
    from .models import VetDoctor, VetSchedule, WEEKDAYS, ClinicBusinessHoursRecord
    
    if not week_start:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
    
    conflicts = []
    doctors = VetDoctor.objects.filter(clinic=clinic, is_active=True)
    
    # 獲取診所營業時間
    business_hours = {}
    business_hours_records = ClinicBusinessHoursRecord.objects.filter(
        clinic=clinic,
        is_default=True,
        status='open'
    ).order_by('weekday', 'start_time')
    
    for record in business_hours_records:
        if record.weekday not in business_hours:
            business_hours[record.weekday] = []
        business_hours[record.weekday].append({
            'start_time': record.start_time,
            'end_time': record.end_time
        })
    
    # 檢查每個醫師的時間衝突
    for doctor in doctors:
        schedules = VetSchedule.objects.filter(
            doctor=doctor,
            is_active=True
        ).order_by('weekday', 'start_time')
        
        # 按天分組
        daily_schedules = {}
        for schedule in schedules:
            if schedule.weekday not in daily_schedules:
                daily_schedules[schedule.weekday] = []
            daily_schedules[schedule.weekday].append(schedule)
        
        # 檢查同一天的時間重疊
        for day, day_schedules in daily_schedules.items():
            for i, schedule1 in enumerate(day_schedules):
                for schedule2 in day_schedules[i+1:]:
                    if time_overlap(schedule1.start_time, schedule1.end_time,
                                  schedule2.start_time, schedule2.end_time):
                        conflicts.append({
                            'type': 'time_overlap',
                            'severity': 'high',
                            'doctor': doctor,
                            'day': day,
                            'day_name': dict(WEEKDAYS)[day],
                            'schedule1': schedule1,
                            'schedule2': schedule2,
                            'message': f'{doctor.user.get_full_name()} 在 {dict(WEEKDAYS)[day]} 有時間重疊'
                        })
            
            # 檢查排班是否超出營業時間
            if day in business_hours:
                for schedule in day_schedules:
                    is_within_business_hours = False
                    for bh in business_hours[day]:
                        if (schedule.start_time >= bh['start_time'] and 
                            schedule.end_time <= bh['end_time']):
                            is_within_business_hours = True
                            break
                    
                    if not is_within_business_hours:
                        conflicts.append({
                            'type': 'outside_business_hours',
                            'severity': 'medium',
                            'doctor': doctor,
                            'day': day,
                            'day_name': dict(WEEKDAYS)[day],
                            'schedule': schedule,
                            'message': f'{doctor.user.get_full_name()} 在 {dict(WEEKDAYS)[day]} 的排班超出營業時間'
                        })
    
    # 檢查診所覆蓋率（只檢查有營業時間的日子）
    for day in range(7):
        if day in business_hours:  # 只檢查有營業的日子
            day_schedules = VetSchedule.objects.filter(
                doctor__clinic=clinic,
                doctor__is_active=True,
                weekday=day,
                is_active=True
            )
            
            if not day_schedules.exists():
                conflicts.append({
                    'type': 'no_coverage',
                    'severity': 'medium',
                    'day': day,
                    'day_name': dict(WEEKDAYS)[day],
                    'message': f'{dict(WEEKDAYS)[day]} 沒有醫師值班（但診所營業中）'
                })
            elif day_schedules.count() == 1:
                # 只有一個醫師值班，可能需要備援
                conflicts.append({
                    'type': 'low_coverage',
                    'severity': 'low',
                    'day': day,
                    'day_name': dict(WEEKDAYS)[day],
                    'message': f'{dict(WEEKDAYS)[day]} 只有一位醫師值班'
                })
    
    return conflicts

def optimize_schedule_suggestions(clinic):
    """
    基於現有排班提供優化建議
    
    Args:
        clinic: VetClinic 實例
    
    Returns:
        list: 優化建議列表
    """
    suggestions = []
    
    # 分析工作量分配
    doctors = VetDoctor.objects.filter(clinic=clinic, is_active=True)
    doctor_workloads = {}
    
    for doctor in doctors:
        schedules = VetSchedule.objects.filter(doctor=doctor, is_active=True)
        total_hours = sum(schedule.duration_hours for schedule in schedules)
        doctor_workloads[doctor] = total_hours
    
    if len(doctor_workloads) > 1:
        avg_workload = sum(doctor_workloads.values()) / len(doctor_workloads)
        
        for doctor, workload in doctor_workloads.items():
            if workload > avg_workload * 1.5:
                suggestions.append({
                    'type': 'workload_balance',
                    'priority': 'medium',
                    'doctor': doctor,
                    'message': f'{doctor.user.get_full_name()} 工作量過重（{workload:.1f}小時），建議重新分配'
                })
            elif workload < avg_workload * 0.5:
                suggestions.append({
                    'type': 'workload_balance',
                    'priority': 'low',
                    'doctor': doctor,
                    'message': f'{doctor.user.get_full_name()} 工作量偏低（{workload:.1f}小時），可增加排班'
                })
    
    return suggestions

def export_schedule_data(clinic, start_date, end_date, format='json'):
    """
    匯出排班資料
    
    Args:
        clinic: VetClinic 實例
        start_date: 開始日期
        end_date: 結束日期
        format: 匯出格式 ('json', 'csv', 'excel')
    
    Returns:
        dict: 匯出的資料
    """
    from .models import VetSchedule, VetDoctor
    
    schedules = VetSchedule.objects.filter(
        doctor__clinic=clinic,
        is_active=True
    ).select_related('doctor__user').order_by('weekday', 'start_time')
    
    export_data = {
        'clinic_name': clinic.clinic_name,
        'export_date': timezone.now().isoformat(),
        'period': {
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        },
        'schedules': []
    }
    
    for schedule in schedules:
        export_data['schedules'].append({
            'doctor_name': schedule.doctor.user.get_full_name(),
            'doctor_email': schedule.doctor.user.email,
            'weekday': schedule.weekday,
            'weekday_name': schedule.get_weekday_display(),
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'duration_hours': schedule.duration_hours,
            'appointment_duration': schedule.appointment_duration,
            'notes': schedule.notes,
            'schedule_type': schedule.schedule_type,
        })
    
    return export_data

# ============ 預約過期處理功能 ============

def process_expired_appointments(days_back=1, mark_as='cancelled'):
    """
    處理過期預約，將過期的預約標記為已取消或未到診
    
    Args:
        days_back: 檢查過去多少天的預約 (預設: 1天)
        mark_as: 標記為什麼狀態 ('cancelled' 或 'no_show')
               - 'cancelled': 已取消（預設，獸醫端自動取消）
               - 'no_show': 未到診（病患未出現）
    
    Returns:
        dict: 處理結果統計
    """
    now = timezone.now()
    start_date = (now - timedelta(days=days_back)).date()
    end_date = now.date()
    
    # 查找可能過期的預約
    potential_expired = VetAppointment.objects.filter(
        slot__date__range=[start_date, end_date],
        status__in=['pending', 'confirmed']
    ).select_related('slot', 'pet')
    
    expired_count = 0
    processed_appointments = []
    
    for appointment in potential_expired:
        if appointment.is_expired:
            previous_status = appointment.status
            if appointment.mark_as_expired(mark_as=mark_as):
                expired_count += 1
                processed_appointments.append({
                    'id': appointment.id,
                    'pet_name': appointment.pet.name,
                    'date': appointment.slot.date,
                    'time': appointment.slot.start_time,
                    'previous_status': previous_status,
                    'new_status': mark_as
                })
                logger.info(f'Marked appointment {appointment.id} as expired ({mark_as})')
    
    result = {
        'processed_count': expired_count,
        'total_checked': potential_expired.count(),
        'date_range': {
            'start': start_date,
            'end': end_date
        },
        'processed_appointments': processed_appointments
    }
    
    if expired_count > 0:
        logger.info(f'Processed {expired_count} expired appointments')
    
    return result

def check_appointment_status(appointment):
    """
    檢查單一預約的狀態
    
    Args:
        appointment: VetAppointment 實例
    
    Returns:
        dict: 預約狀態資訊
    """
    now = timezone.now()
    appointment_datetime = datetime.combine(appointment.slot.date, appointment.slot.start_time)
    appointment_datetime = timezone.make_aware(appointment_datetime)
    
    return {
        'id': appointment.id,
        'current_status': appointment.status,
        'is_expired': appointment.is_expired,
        'is_today': appointment.is_today,
        'is_future': appointment.is_future,
        'time_until_appointment': (appointment_datetime - now).total_seconds() / 3600,  # 小時
        'can_be_processed': appointment.status in ['pending', 'confirmed'] and appointment.is_expired
    }

def get_expired_appointments_summary(clinic=None, days_back=7):
    """
    獲取過期預約摘要
    
    Args:
        clinic: VetClinic 實例，如果提供則僅查看該診所
        days_back: 檢查過去多少天的預約
    
    Returns:
        dict: 過期預約摘要
    """
    now = timezone.now()
    start_date = (now - timedelta(days=days_back)).date()
    
    query_filter = {
        'slot__date__gte': start_date,
        'status__in': ['pending', 'confirmed']
    }
    
    if clinic:
        query_filter['slot__doctor__clinic'] = clinic
    
    appointments = VetAppointment.objects.filter(**query_filter).select_related('slot', 'pet')
    
    expired_appointments = []
    for appointment in appointments:
        if appointment.is_expired:
            expired_appointments.append(appointment)
    
    return {
        'total_expired': len(expired_appointments),
        'total_checked': appointments.count(),
        'expired_appointments': expired_appointments,
        'check_period_days': days_back,
        'last_check': now
    }

# ============ 智能健康儀表板功能 ============

def calculate_pet_health_score(pet):
    """
    計算寵物的健康評分（0-100分）
    
    基於以下因素：
    - 疫苗接種狀況 (30分)
    - 驅蟲記錄 (20分)
    - 最近醫療記錄 (30分)
    - 日常健康數據 (20分)
    """
    total_score = 0
    now = timezone.now().date()
    
    # 疫苗接種評分 (30分)
    vaccine_score = _calculate_vaccine_score(pet, now)
    total_score += vaccine_score
    
    # 驅蟲記錄評分 (20分)
    deworm_score = _calculate_deworm_score(pet, now)
    total_score += deworm_score
    
    # 醫療記錄評分 (30分)
    medical_score = _calculate_medical_score(pet, now)
    total_score += medical_score
    
    # 日常健康數據評分 (20分)
    daily_score = _calculate_daily_health_score(pet, now)
    total_score += daily_score
    
    return min(100, max(0, total_score))

def _calculate_vaccine_score(pet, current_date):
    """計算疫苗接種評分"""
    latest_vaccine = VaccineRecord.objects.filter(pet=pet).order_by('-date').first()
    
    if not latest_vaccine:
        return 0  # 無疫苗記錄
    
    days_since_vaccine = (current_date - latest_vaccine.date).days
    
    if days_since_vaccine <= 365:  # 一年內
        return 30
    elif days_since_vaccine <= 548:  # 18個月內
        return 20
    else:
        return 5  # 超過18個月，需要補強

def _calculate_deworm_score(pet, current_date):
    """計算驅蟲記錄評分"""
    latest_deworm = DewormRecord.objects.filter(pet=pet).order_by('-date').first()
    
    if not latest_deworm:
        return 0  # 無驅蟲記錄
    
    days_since_deworm = (current_date - latest_deworm.date).days
    
    if days_since_deworm <= 90:  # 三個月內
        return 20
    elif days_since_deworm <= 180:  # 六個月內
        return 15
    else:
        return 5  # 超過六個月

def _calculate_medical_score(pet, current_date):
    """計算醫療記錄評分"""
    # 檢查最近6個月的醫療記錄
    six_months_ago = current_date - timedelta(days=180)
    recent_records = MedicalRecord.objects.filter(
        pet=pet,
        created_at__date__gte=six_months_ago
    ).order_by('-created_at')
    
    if not recent_records.exists():
        return 30  # 無醫療記錄表示健康
    
    # 根據醫療記錄的嚴重程度評分
    emergency_keywords = ['緊急', '急診', '重病', '手術', '住院']
    concern_keywords = ['感染', '發燒', '嘔吐', '腹瀉', '食慾不振']
    
    total_records = recent_records.count()
    emergency_count = 0
    concern_count = 0
    
    for record in recent_records:
        content = (record.diagnosis or '') + (record.treatment_plan or '') + (record.notes or '')
        if any(keyword in content for keyword in emergency_keywords):
            emergency_count += 1
        elif any(keyword in content for keyword in concern_keywords):
            concern_count += 1
    
    if emergency_count > 0:
        return 10  # 有緊急醫療記錄
    elif concern_count > total_records * 0.5:
        return 20  # 超過一半是需要關注的記錄
    else:
        return 30  # 醫療記錄正常

def _calculate_daily_health_score(pet, current_date):
    """計算日常健康數據評分"""
    # 檢查最近30天的體溫和體重記錄
    thirty_days_ago = current_date - timedelta(days=30)
    
    temp_records = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__gte=thirty_days_ago
    ).order_by('-date')
    
    weight_records = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__gte=thirty_days_ago
    ).order_by('-date')
    
    score = 20
    
    # 體溫異常檢查
    for record in temp_records[:10]:  # 檢查最近10筆記錄
        try:
            temp = float(record.content)
            if temp < 37.5 or temp > 39.5:  # 犬貓正常體溫範圍
                score -= 2
        except ValueError:
            continue
    
    # 體重急劇變化檢查
    if weight_records.count() >= 2:
        try:
            latest_weight = float(weight_records.first().content)
            earliest_weight = float(weight_records.last().content)
            weight_change_percent = abs(latest_weight - earliest_weight) / earliest_weight * 100
            
            if weight_change_percent > 10:  # 體重變化超過10%
                score -= 5
        except (ValueError, ZeroDivisionError):
            pass
    
    return max(0, score)

def get_health_alerts(pet):
    """
    獲取寵物的健康警報
    
    Returns:
        list: 警報列表，每個警報包含 type, severity, message, action
    """
    alerts = []
    now = timezone.now().date()
    
    # 疫苗過期警報
    vaccine_alert = _check_vaccine_alert(pet, now)
    if vaccine_alert:
        alerts.append(vaccine_alert)
    
    # 驅蟲過期警報
    deworm_alert = _check_deworm_alert(pet, now)
    if deworm_alert:
        alerts.append(deworm_alert)
    
    # 醫療追蹤警報
    medical_alerts = _check_medical_alerts(pet, now)
    alerts.extend(medical_alerts)
    
    # 體重異常警報
    weight_alert = _check_weight_alert(pet, now)
    if weight_alert:
        alerts.append(weight_alert)
    
    return sorted(alerts, key=lambda x: {'urgent': 3, 'warning': 2, 'info': 1}[x['severity']], reverse=True)

def _check_vaccine_alert(pet, current_date):
    """檢查疫苗警報"""
    latest_vaccine = VaccineRecord.objects.filter(pet=pet).order_by('-date').first()
    
    if not latest_vaccine:
        return {
            'type': 'vaccine',
            'severity': 'urgent',
            'message': '尚未接種疫苗',
            'action': '建議盡快安排疫苗接種'
        }
    
    days_since_vaccine = (current_date - latest_vaccine.date).days
    
    if days_since_vaccine > 548:  # 18個月
        return {
            'type': 'vaccine',
            'severity': 'urgent',
            'message': f'疫苗已過期 {days_since_vaccine - 365} 天',
            'action': '緊急需要補強疫苗'
        }
    elif days_since_vaccine > 365:  # 一年
        return {
            'type': 'vaccine',
            'severity': 'warning',
            'message': '疫苗即將到期',
            'action': '建議安排疫苗補強'
        }
    
    return None

def _check_deworm_alert(pet, current_date):
    """檢查驅蟲警報"""
    latest_deworm = DewormRecord.objects.filter(pet=pet).order_by('-date').first()
    
    if not latest_deworm:
        return {
            'type': 'deworm',
            'severity': 'warning',
            'message': '尚未進行驅蟲',
            'action': '建議安排驅蟲治療'
        }
    
    days_since_deworm = (current_date - latest_deworm.date).days
    
    if days_since_deworm > 180:  # 六個月
        return {
            'type': 'deworm',
            'severity': 'warning',
            'message': f'驅蟲已過期 {days_since_deworm - 90} 天',
            'action': '建議安排驅蟲治療'
        }
    elif days_since_deworm > 90:  # 三個月
        return {
            'type': 'deworm',
            'severity': 'info',
            'message': '驅蟲即將到期',
            'action': '可安排下次驅蟲'
        }
    
    return None

def _check_medical_alerts(pet, current_date):
    """檢查醫療追蹤警報"""
    alerts = []
    
    # 檢查是否有需要追蹤的醫療記錄
    recent_records = MedicalRecord.objects.filter(
        pet=pet,
        created_at__date__gte=current_date - timedelta(days=30)
    ).order_by('-created_at')
    
    follow_up_keywords = ['回診', '追蹤', '複檢', '再次檢查']
    
    for record in recent_records[:5]:  # 檢查最近5筆記錄
        content = (record.treatment_plan or '') + (record.notes or '')
        if any(keyword in content for keyword in follow_up_keywords):
            alerts.append({
                'type': 'medical_followup',
                'severity': 'info',
                'message': f'需要追蹤 {record.created_at.strftime("%m/%d")} 的醫療記錄',
                'action': '安排回診檢查'
            })
    
    return alerts

def _check_weight_alert(pet, current_date):
    """檢查體重異常警報"""
    recent_weights = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__gte=current_date - timedelta(days=60)
    ).order_by('-date')[:5]
    
    if recent_weights.count() < 2:
        return None
    
    try:
        weights = [float(record.content) for record in recent_weights]
        latest_weight = weights[0]
        avg_previous_weight = sum(weights[1:]) / len(weights[1:])
        
        weight_change_percent = abs(latest_weight - avg_previous_weight) / avg_previous_weight * 100
        
        if weight_change_percent > 15:
            severity = 'urgent' if weight_change_percent > 25 else 'warning'
            direction = '增加' if latest_weight > avg_previous_weight else '減少'
            return {
                'type': 'weight_change',
                'severity': severity,
                'message': f'體重{direction} {weight_change_percent:.1f}%',
                'action': '建議諮詢獸醫師'
            }
    except (ValueError, ZeroDivisionError):
        pass
    
    return None

def get_health_insights(pet):
    """
    獲取寵物的健康洞察
    
    Returns:
        dict: 包含健康評分、警報、趨勢等資訊
    """
    health_score = calculate_pet_health_score(pet)
    alerts = get_health_alerts(pet)
    
    # 健康狀態評級
    if health_score >= 85:
        health_status = 'excellent'
        status_text = '健康狀況優良'
        status_color = 'success'
    elif health_score >= 70:
        health_status = 'good'
        status_text = '健康狀況良好'
        status_color = 'primary'
    elif health_score >= 50:
        health_status = 'fair'
        status_text = '健康狀況尚可'
        status_color = 'warning'
    else:
        health_status = 'poor'
        status_text = '需要關注健康狀況'
        status_color = 'danger'
    
    # 獲取最近的體重和體溫趨勢
    now = timezone.now().date()
    weight_trend = _get_weight_trend(pet, now)
    temp_trend = _get_temperature_trend(pet, now)
    
    return {
        'health_score': health_score,
        'health_status': health_status,
        'status_text': status_text,
        'status_color': status_color,
        'alerts': alerts,
        'urgent_alerts_count': len([a for a in alerts if a['severity'] == 'urgent']),
        'warning_alerts_count': len([a for a in alerts if a['severity'] == 'warning']),
        'weight_trend': weight_trend,
        'temperature_trend': temp_trend,
        'last_updated': now
    }

def _get_weight_trend(pet, current_date):
    """獲取體重趨勢"""
    recent_weights = DailyRecord.objects.filter(
        pet=pet,
        category='weight',
        date__gte=current_date - timedelta(days=30)
    ).order_by('-date')[:10]
    
    if recent_weights.count() < 2:
        return {'status': 'no_data', 'message': '數據不足'}
    
    try:
        weights = [(record.date, float(record.content)) for record in reversed(recent_weights)]
        
        if len(weights) >= 3:
            recent_avg = sum(w[1] for w in weights[-3:]) / 3
            earlier_avg = sum(w[1] for w in weights[:-3]) / len(weights[:-3])
            change_percent = (recent_avg - earlier_avg) / earlier_avg * 100
            
            if change_percent > 5:
                return {'status': 'increasing', 'message': f'體重上升 {change_percent:.1f}%', 'trend': 'up'}
            elif change_percent < -5:
                return {'status': 'decreasing', 'message': f'體重下降 {abs(change_percent):.1f}%', 'trend': 'down'}
            else:
                return {'status': 'stable', 'message': '體重穩定', 'trend': 'stable'}
    except (ValueError, ZeroDivisionError):
        pass
    
    return {'status': 'stable', 'message': '體重穩定', 'trend': 'stable'}

def _get_temperature_trend(pet, current_date):
    """獲取體溫趨勢"""
    recent_temps = DailyRecord.objects.filter(
        pet=pet,
        category='temperature',
        date__gte=current_date - timedelta(days=14)
    ).order_by('-date')[:7]
    
    if recent_temps.count() < 2:
        return {'status': 'no_data', 'message': '數據不足'}
    
    try:
        temps = [float(record.content) for record in recent_temps]
        avg_temp = sum(temps) / len(temps)
        
        # 檢查是否有異常體溫
        abnormal_count = len([t for t in temps if t < 37.5 or t > 39.5])
        
        if abnormal_count > len(temps) * 0.5:
            return {'status': 'abnormal', 'message': '體溫異常', 'trend': 'warning'}
        elif 38.0 <= avg_temp <= 39.0:
            return {'status': 'normal', 'message': f'體溫正常 ({avg_temp:.1f}°C)', 'trend': 'normal'}
        else:
            return {'status': 'attention', 'message': f'需注意體溫 ({avg_temp:.1f}°C)', 'trend': 'caution'}
    except ValueError:
        pass
    
    return {'status': 'normal', 'message': '體溫正常', 'trend': 'normal'}