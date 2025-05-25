import requests
import logging
import re
import unicodedata
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from .models import AdoptionAnimal, AdoptionShelter
import pytz

logger = logging.getLogger(__name__)

class AdoptionDataSyncService:
    """動物認領養資料同步服務"""
    
    API_URL = "https://data.moa.gov.tw/Service/OpenData/TransService.aspx?UnitId=QcbUEzN6E6DL"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Pet Management System/1.0'
        })
        # 設定台灣時區
        self.taiwan_tz = pytz.timezone('Asia/Taipei')
    
    def safe_encode(self, text, max_length=None):
        """安全編碼文字，處理特殊字符"""
        if not text:
            return ''
        
        try:
            # 確保是字符串
            text = str(text)
            
            # 正規化Unicode字符
            text = unicodedata.normalize('NFKC', text)
            
            # 移除控制字符但保留基本空白字符
            text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\t\n\r ')
            
            # 替換可能有問題的字符
            problematic_chars = {
                '\ufffd': '',  # 替換字符
                '\u200b': '',  # 零寬度空格
                '\u200c': '',  # 零寬度非連接符
                '\u200d': '',  # 零寬度連接符
                '\ufeff': '',  # 字節順序標記
            }
            
            for old_char, new_char in problematic_chars.items():
                text = text.replace(old_char, new_char)
            
            # 清理多餘空白
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 限制長度
            if max_length and len(text) > max_length:
                text = text[:max_length].rstrip()
            
            return text
            
        except Exception as e:
            logger.warning(f"編碼文字時發生錯誤 '{text}': {e}")
            return ''
    
    def fetch_api_data(self):
        """從API取得資料"""
        try:
            response = self.session.get(self.API_URL, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API請求失敗: {e}")
            raise
    
    def parse_datetime(self, date_str):
        """解析日期時間字串並加上時區資訊"""
        if not date_str:
            return None
        
        try:
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d'
            ]
            
            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if dt is None:
                return None
            
            # 如果解析的日期時間沒有時區資訊，加上台灣時區
            if dt.tzinfo is None:
                dt = self.taiwan_tz.localize(dt)
            
            # 轉換為Django的aware datetime
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            
        except Exception as e:
            logger.warning(f"無法解析日期時間 '{date_str}': {e}")
            return None
    
    def sync_shelters(self, animals_data):
        """同步收容所資料"""
        shelters_to_create = set()
        
        for animal_data in animals_data:
            # 收集收容所資料
            if animal_data.get('animal_shelter_pkid'):
                shelters_to_create.add((
                    animal_data['animal_shelter_pkid'],
                    self.safe_encode(animal_data.get('shelter_name', ''), 100),
                    self.safe_encode(animal_data.get('shelter_address', ''), 200),
                    self.safe_encode(animal_data.get('shelter_tel', ''), 50)
                ))
                
        # 建立收容所資料
        for shelter_data in shelters_to_create:
            try:
                shelter_code, name, address, tel = shelter_data
                
                if shelter_code:  # 確保有收容所代碼
                    AdoptionShelter.objects.get_or_create(
                        shelter_code=shelter_code,
                        defaults={
                            'shelter_name': name,
                            'address': address,
                            'phone': tel
                        }
                    )
            except Exception as e:
                logger.error(f"建立收容所資料失敗 {shelter_code}: {e}")
    
    def sync_animals(self, animals_data):
        """同步動物資料"""
        updated_count = 0
        created_count = 0
        error_count = 0
        
        for i, animal_data in enumerate(animals_data):
            try:
                animal_id = animal_data.get('animal_id')
                if not animal_id:
                    continue
                
                # 清理animal_id
                animal_id = self.safe_encode(animal_id, 50)
                
                # 準備資料並清理文字（移除了 area 和 city 相關處理）
                animal_defaults = {
                    'shelter_pkid': self.safe_encode(animal_data.get('shelter_pkid', ''), 50),
                    'animal_area_pkid': animal_data.get('animal_area_pkid'),
                    'animal_shelter_pkid': animal_data.get('animal_shelter_pkid'),
                    'animal_place': self.safe_encode(animal_data.get('animal_place', ''), 100),
                    'animal_kind': self.safe_encode(animal_data.get('animal_kind', ''), 50),
                    'animal_variety': self.safe_encode(animal_data.get('animal_Variety', ''), 100),
                    'animal_sex': self.safe_encode(animal_data.get('animal_sex', ''), 20),
                    'animal_bodytype': self.safe_encode(animal_data.get('animal_bodytype', ''), 20),
                    'animal_colour': self.safe_encode(animal_data.get('animal_colour', ''), 50),
                    'animal_age': self.safe_encode(animal_data.get('animal_age', ''), 20),
                    'animal_sterilization': self.safe_encode(animal_data.get('animal_sterilization', ''), 20),
                    'animal_bacterin': self.safe_encode(animal_data.get('animal_bacterin', ''), 20),
                    'animal_foundplace': self.safe_encode(animal_data.get('animal_foundplace', ''), 200),
                    'animal_title': self.safe_encode(animal_data.get('animal_title', ''), 200),
                    'animal_status': self.safe_encode(animal_data.get('animal_status', ''), 50),
                    'animal_remark': self.safe_encode(animal_data.get('animal_remark', ''), 1000),
                    'animal_caption': self.safe_encode(animal_data.get('animal_caption', ''), 1000),
                    'animal_opendate': self.parse_datetime(animal_data.get('animal_opendate')),
                    'animal_closeddate': self.parse_datetime(animal_data.get('animal_closeddate')),
                    'animal_update': self.parse_datetime(animal_data.get('animal_update')),
                    'animal_createtime': self.parse_datetime(animal_data.get('animal_createtime')),
                    'shelter_name': self.safe_encode(animal_data.get('shelter_name', ''), 100),
                    'shelter_address': self.safe_encode(animal_data.get('shelter_address', ''), 200),
                    'shelter_tel': self.safe_encode(animal_data.get('shelter_tel', ''), 50),
                    'album_file': animal_data.get('album_file', '') or '',
                    'album_update': self.parse_datetime(animal_data.get('album_update')),
                    'animal_subid': self.safe_encode(animal_data.get('animal_subid', ''), 50),
                    'cdate': self.parse_datetime(animal_data.get('cDate')),
                }
                
                # 建立或更新動物資料
                animal, created = AdoptionAnimal.objects.get_or_create(
                    animal_id=animal_id,
                    defaults=animal_defaults
                )
                
                if created:
                    created_count += 1
                else:
                    # 更新現有資料
                    for key, value in animal_defaults.items():
                        setattr(animal, key, value)
                    animal.save()
                    updated_count += 1
                
                # 每處理100筆資料顯示進度
                if (i + 1) % 100 == 0:
                    logger.info(f"已處理 {i + 1}/{len(animals_data)} 筆資料")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"處理動物資料 {animal_data.get('animal_id', 'unknown')} 時發生錯誤: {e}")
                
                # 如果錯誤太多，停止處理
                if error_count > 50:
                    logger.error("錯誤數量過多，停止同步")
                    break
                    
                continue
        
        return created_count, updated_count, error_count
    
    @transaction.atomic
    def sync_all_data(self):
        """完整資料同步"""
        try:
            logger.info("開始同步動物認領養資料...")
            
            # 取得API資料
            animals_data = self.fetch_api_data()
            logger.info(f"從API取得 {len(animals_data)} 筆資料")
            
            # 同步收容所資料
            logger.info("同步收容所資料...")
            self.sync_shelters(animals_data)
            
            # 同步動物資料
            logger.info("同步動物資料...")
            created_count, updated_count, error_count = self.sync_animals(animals_data)
            
            message = f"新增 {created_count} 筆，更新 {updated_count} 筆"
            if error_count > 0:
                message += f"，跳過 {error_count} 筆有問題的資料"
            
            logger.info(f"資料同步完成 - {message}")
            return True, message
            
        except Exception as e:
            logger.error(f"資料同步失敗: {e}")
            return False, str(e)