# PetApp ERD（分模組，含所有欄位）

_Generated: 2025-09-27T13:51:24_


以下 8 個模組皆為 GitHub 相容的 Mermaid ERD。

## 1) 診所與人員（Clinic & Staff）

```mermaid
erDiagram
  AUTH_USER ||--|| Profile : r1
  AUTH_USER ||--|| VetDoctor : r2
  VetClinic ||--|| ClinicScheduleRule : r3
  VetClinic ||--o{ ClinicBusinessHoursRecord : r4
  VetClinic ||--o{ VetDoctor : r5
  VetClinic ||--o{ ClinicBusinessHoursTemplate : r6

  AUTH_USER {
    int id
    string username
    string email
    string first_name
    string last_name
    string password
    bool is_staff
    bool is_active
    bool is_superuser
    datetime last_login
    datetime date_joined
  }
  Profile {
    int id
    int user_id
    string account_type
    string phone_number
  }
  VetClinic {
    int id
    string clinic_name
    string license_number
    string clinic_phone
    string clinic_address
    string clinic_email
    int clinic_admin_id
    bool is_verified
    datetime verification_date
    string moa_county
    string moa_status
    string moa_responsible_vet
    date moa_issue_date
    int default_appointment_duration
    int advance_booking_days
    string clinic_mode
    datetime created_at
    datetime updated_at
  }
  VetDoctor {
    int id
    int user_id
    int clinic_id
    string vet_license_number
    bool license_verified_with_moa
    datetime verification_date
    string moa_license_type
    string moa_clinic_name
    string specialization
    int years_of_experience
    text bio
    bool is_active_veterinarian
    bool is_clinic_admin
    bool is_active
    datetime created_at
    datetime updated_at
  }
  ClinicBusinessHoursRecord {
    int id
    int clinic_id
    int weekday
    time start_time
    time end_time
    string status
    int order
    date effective_date
    bool is_default
    text notes
    datetime created_at
    datetime updated_at
    int created_by_id
  }
  ClinicBusinessHoursTemplate {
    int id
    string name
    string template_type
    text description
    json template_data
    bool is_system_template
    datetime created_at
    datetime updated_at
  }
  ClinicScheduleRule {
    int id
    int clinic_id
    int min_shift_duration
    int max_shift_duration
    int min_break_between_shifts
    int max_work_hours_per_week
    int max_consecutive_work_days
    int min_doctors_per_shift
    int max_doctors_per_shift
    int min_leave_notice_days
    int max_consecutive_leave_days
    int auto_approve_leave_hours
    bool require_substitute_for_leave
    bool notify_schedule_changes
    bool notify_conflict_detection
    datetime created_at
    datetime updated_at
  }
```

## 2) 排班與預約（Scheduling & Booking）

```mermaid
erDiagram
  VetDoctor ||--o{ VetSchedule : r1
  VetDoctor ||--o{ VetScheduleException : r2
  VetDoctor ||--o{ AppointmentSlot : r3
  VetDoctor ||--o{ EnhancedVetSchedule : r4
  VetClinic ||--o{ AppointmentSlot : r5
  AppointmentSlot ||--o{ VetAppointment : r6
  AUTH_USER ||--o{ VetAppointment : r7
  Pet ||--o{ VetAppointment : r8
  ScheduleTemplate ||--o{ EnhancedVetSchedule : r9
  EnhancedVetSchedule ||--o{ ScheduleChangeRequest : r10
  EnhancedVetSchedule ||--o{ EnhancedVetSchedule : r11

  VetSchedule {
    int id
    int doctor_id
    int weekday
    time start_time
    time end_time
    int appointment_duration
    int max_appointments_per_slot
    text notes
    bool is_active
    datetime created_at
    datetime updated_at
    string schedule_type
    string priority
    string status
    bool has_conflicts
    json conflict_details
    date valid_from
    date valid_until
    int copied_from_id
    string batch_group
  }
  VetScheduleException {
    int id
    int doctor_id
    string exception_type
    date start_date
    date end_date
    time start_time
    time end_time
    time alternative_start_time
    time alternative_end_time
    text reason
    bool is_active
    int created_by_id
    datetime created_at
  }
  AppointmentSlot {
    int id
    int clinic_id
    int doctor_id
    date date
    time start_time
    time end_time
    bool is_available
    int max_bookings
    int current_bookings
    string source
    datetime created_at
  }
  VetAppointment {
    int id
    int pet_id
    int owner_id
    int slot_id
    text reason
    text notes
    string status
    string contact_phone
    string contact_email
    string booking_type
    bool clinic_notified
    bool reminder_sent
    datetime created_at
    datetime updated_at
  }
  ScheduleTemplate {
    int id
    string name
    text description
    string template_type
    string schedule_pattern
    int created_by_id
    int clinic_id
    json template_data
    int usage_count
    bool is_active
    bool is_public
    datetime created_at
    datetime updated_at
  }
  EnhancedVetSchedule {
    int id
    int doctor_id
    int clinic_id
    string title
    string schedule_type
    date start_date
    date end_date
    json weekdays
    json daily_time_slots
    int appointment_duration
    int max_appointments_per_slot
    int buffer_time
    string status
    string priority
    int approved_by_id
    datetime approved_at
    text notes
    bool is_holiday_excluded
    int created_from_template_id
    int parent_schedule_id
    bool has_conflicts
    json conflict_details
    int created_by_id
    datetime created_at
    datetime updated_at
  }
  ScheduleChangeRequest {
    int id
    int requestor_id
    int clinic_id
    string request_type
    text reason
    int original_schedule_id
    date change_start_date
    date change_end_date
    time change_start_time
    time change_end_time
    int substitute_doctor_id
    string status
    int reviewed_by_id
    datetime reviewed_at
    text review_notes
    datetime created_at
    datetime updated_at
  }
  VetClinic {
    int id
    string clinic_name
  }
  VetDoctor {
    int id
    int user_id
  }
  AUTH_USER {
    int id
    string username
  }
  Pet {
    int id
    string name
  }
```

## 3) 寵物、標籤與日誌（Pets, Tags & Daily）

```mermaid
erDiagram
  AUTH_USER ||--o{ Pet : r1
  Pet ||--o{ DailyRecord : r2
  Pet ||--o{ VaccineRecord : r3
  Pet ||--o{ DewormRecord : r4
  Pet ||--o{ Report : r5
  Pet ||--o{ MedicalRecord : r6
  Pet }o--o{ PetTag : r7
  VetDoctor ||--o{ VaccineRecord : r8
  VetDoctor ||--o{ DewormRecord : r9
  VetDoctor ||--o{ MedicalRecord : r10
  Profile ||--o{ Report : r11

  Pet {
    int id
    int owner_id
    string species
    string breed
    string name
    string sterilization_status
    string chip
    date birth_date
    string gender
    float weight
    text feature
    string picture
    date last_visit_date
    bool is_active
    string emergency_contact
    string emergency_phone
    text medical_notes
    bool is_adoption_only
    bool is_adopted
    datetime created_at
    datetime updated_at
  }
  PetTag {
    int id
    string name
    string tag_type
    string color
    text description
    bool is_system_tag
    datetime created_at
  }
  DailyRecord {
    int id
    int pet_id
    date date
    datetime created_at
    string category
    text content
    decimal temperature
    decimal weight
    string medication_dosage
    int exercise_duration
  }
  VaccineRecord {
    int id
    int pet_id
    string name
    date date
    string location
    int vet_id
    int protection_period_months
    date next_due_date
  }
  DewormRecord {
    int id
    int pet_id
    string name
    date date
    string location
    int vet_id
    int protection_period_months
    date next_due_date
  }
  Report {
    int id
    int pet_id
    int vet_id
    int clinic_id
    string title
    string pdf
    datetime date_uploaded
  }
  MedicalRecord {
    int id
    int pet_id
    int attending_vet_id
    int recorded_by_id
    date visit_date
    string clinic_location
    decimal weight
    decimal temperature
    int heart_rate
    int respiratory_rate
    text chief_complaint
    text physical_examination
    text diagnosis
    int diagnosis_confidence
    text treatment
    text treatment_plan
    bool follow_up_required
    date follow_up_date
    decimal total_cost
    text notes
    datetime created_at
  }
  VetDoctor {
    int id
    int user_id
  }
  Profile {
    int id
    int user_id
  }
  AUTH_USER {
    int id
    string username
  }
```

## 4) 地點與服務（Locations & Services）

```mermaid
erDiagram
  PetLocation }o--o{ ServiceType : r1
  PetLocation }o--o{ PetType : r2
  PetLocation ||--o{ BusinessHours : r3

  ServiceType {
    int id
    string name
    string code
    bool is_active
  }
  PetType {
    int id
    string name
    string code
    bool is_active
  }
  PetLocation {
    int id
    string name
    string address
    string phone
    text website
    string city
    string district
    decimal lat
    decimal lon
    decimal rating
    int rating_count
    bool has_emergency
    json business_hours
    datetime created_at
    datetime updated_at
  }
  BusinessHours {
    int id
    int location_id
    int day_of_week
    time open_time
    time close_time
    int period_order
    string period_name
  }
```

## 5) 領養（Adoption）

```mermaid
erDiagram
  AUTH_USER ||--o{ AdoptionPet : r1
  AdoptionPet ||--o{ AdoptionTransferRequest : r2
  Pet ||--o{ AdoptionPet : r3
  AUTH_USER ||--o{ TransferRequest : r4
  AUTH_USER ||--o{ TransferRequest : r5
  Pet ||--o{ TransferRequest : r6

  AdoptionPet {
    int id
    int owner_id
    string species
    string breed
    string name
    string sterilization_status
    string chip
    date birth_date
    string gender
    float weight
    string vaccine
    text feature
    string adopt_picture1
    bool is_adopted
    datetime posted_date
    string physical_condition
    string adoption_condition
    string adopt_picture2
    string adopt_picture3
    string adopt_picture4
    string phone
    string line_id
    string adopt_place
    int original_pet_id
    bool is_publish
    string health_certificate
    string vaccine_certificate
  }
  AdoptionTransferRequest {
    int id
    int adoption_id
    int from_owner_id
    string to_email
    string to_phone
    int to_user_id
    text transfer_note
    string status
    datetime created_at
    bool from_owner_has_seen
    bool to_user_has_seen
  }
  TransferRequest {
    int id
    int pet_id
    int from_owner_id
    string to_email
    string to_phone
    int to_user_id
    string status
    datetime created_at
    bool from_owner_has_seen
    bool to_user_has_seen
  }
  Pet {
    int id
    string name
  }
  AUTH_USER {
    int id
    string username
  }
```

## 6) 社群（Social）

```mermaid
erDiagram
  AUTH_USER ||--|| UserProfile : r1
  AUTH_USER ||--o{ Post : r2
  AUTH_USER ||--o{ Follow : r3
  AUTH_USER ||--o{ Like : r4
  AUTH_USER ||--o{ Comment : r5
  AUTH_USER ||--o{ CommentLike : r6
  Post ||--o{ PostMedia : r7
  Post ||--o{ Comment : r8
  Post ||--o{ Like : r9
  Post ||--o{ Post : r10
  Comment ||--o{ Comment : r11
  Comment ||--o{ CommentLike : r12

  UserProfile {
    int id
    int user_id
    text bio
    string avatar
    string banner
    int followers_count
    int following_count
    int posts_count
    datetime created_at
    datetime updated_at
  }
  Follow {
    int id
    int follower_id
    int following_id
    datetime created_at
  }
  Post {
    uuid id
    int user_id
    text content
    string post_type
    string location
    int likes_count
    int comments_count
    int shares_count
    uuid original_post_id
    bool is_repost
    datetime created_at
    datetime updated_at
  }
  PostMedia {
    uuid id
    uuid post_id
    string media_type
    string file
    int order
    datetime created_at
  }
  Like {
    int id
    int user_id
    uuid post_id
    datetime created_at
  }
  Comment {
    uuid id
    int user_id
    uuid post_id
    text content
    uuid parent_comment_id
    int likes_count
    datetime created_at
    datetime updated_at
  }
  CommentLike {
    int id
    int user_id
    uuid comment_id
    datetime created_at
  }
  AUTH_USER {
    int id
    string username
  }
```

## 7) 客服與通知（Handoff & Notifications）

```mermaid
erDiagram
  HandoffTicket ||--o{ HandoffMessage : r1
  AUTH_USER ||--o{ Notification : r2
  Post ||--o{ Notification : r3
  Comment ||--o{ Notification : r4

  HandoffTicket {
    int id
    string session_key
    string name
    string contact
    string channel
    bool is_open
    datetime created_at
  }
  HandoffMessage {
    int id
    int ticket_id
    string sender
    text text
    datetime created_at
  }
  Notification {
    int id
    int recipient_id
    int sender_id
    string notification_type
    string title
    text message
    bool is_read
    datetime created_at
    uuid post_id
    uuid comment_id
  }
  Post {
    uuid id
    int user_id
  }
  Comment {
    uuid id
    int user_id
  }
  AUTH_USER {
    int id
    string username
  }
```

## 8) 其他資料（Other Data）

```mermaid
erDiagram

  AnimalDrug {
    int id
    string license_number
    string chinese_name
    string english_name
    string manufacturer
    string applicant
    string dosage_form
    string packaging
    text indications
    text active_ingredients
    string target_animals
    bool is_active
    datetime sync_date
    datetime created_at
    datetime updated_at
  }
  VetAvailableTime {
    int id
    int vet_id
    int weekday
    string time_slot
    time start_time
    time end_time
    datetime created_at
    datetime updated_at
  }
```
