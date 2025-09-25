from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
import json
import logging
from petapp.models import *

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '從政府開放資料API同步動物用藥資訊'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='同步資料筆數限制 (默認: 500)'
        )
        parser.add_argument(
            '--skip',
            type=int, 
            default=0,
            help='跳過前N筆資料 (默認: 0)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制更新已存在的資料'
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        skip = options['skip'] 
        force_update = options['force']
        
        self.stdout.write(f"開始同步動物用藥資料... (limit={limit}, skip={skip})")
        
        # 政府開放資料API網址
        url = f"https://data.moa.gov.tw/Service/OpenData/FromM/ADProData.aspx?$top={limit}&$skip={skip}&UnitId=023"
        
        try:
            # 發送HTTP請求
            self.stdout.write("正在連接政府開放資料API...")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # 解析JSON資料
            try:
                data = response.json()
                if not isinstance(data, list):
                    self.stdout.write(self.style.ERROR("API返回的不是陣列格式"))
                    return
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f"JSON解析失敗: {e}"))
                return
            
            self.stdout.write(f"成功獲取 {len(data)} 筆資料")
            
            # 處理每筆資料
            created_count = 0
            updated_count = 0
            error_count = 0
            
            for index, item in enumerate(data):
                try:
                    # 提取資料欄位（處理可能的欄位名稱變化）
                    license_number = self._get_field_value(item, ['許可證字號', 'LicenseNo', 'license_number'])
                    if not license_number:
                        self.stdout.write(f"第 {index+1} 筆資料缺少許可證字號，跳過")
                        error_count += 1
                        continue
                    
                    chinese_name = self._get_field_value(item, ['動物用藥品中文品名', '中文品名', 'ChineseName', 'chinese_name'])
                    english_name = self._get_field_value(item, ['動物用藥品英文品名', '英文品名', 'EnglishName', 'english_name'])
                    manufacturer = self._get_field_value(item, ['製造廠名稱', 'Manufacturer', 'manufacturer'])
                    applicant = self._get_field_value(item, ['申請商名稱', 'Applicant', 'applicant'])
                    dosage_form = self._get_field_value(item, ['劑型', 'DosageForm', 'dosage_form'])
                    packaging = self._get_field_value(item, ['包裝', 'Package', 'packaging'])
                    indications = self._get_field_value(item, ['效能(適應症)', '效能', 'Indications', 'indications'])
                    ingredients = self._get_field_value(item, ['成分', 'Ingredients', 'ingredients'])
                    # 從效能(適應症)欄位中提取適用動物資訊
                    target_animals = self._extract_target_animals(indications)
                    
                    # 檢查是否已存在
                    drug, created = AnimalDrug.objects.get_or_create(
                        license_number=license_number,
                        defaults={
                            'chinese_name': chinese_name or '',
                            'english_name': english_name or '',
                            'manufacturer': manufacturer or '',
                            'applicant': applicant or '',
                            'dosage_form': dosage_form or '',
                            'packaging': packaging or '',
                            'indications': indications or '',
                            'active_ingredients': ingredients or '',
                            'target_animals': target_animals or '',
                            'is_active': True,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(f"[+] 新增: {chinese_name}")
                    elif force_update:
                        # 更新現有資料
                        drug.chinese_name = chinese_name or drug.chinese_name
                        drug.english_name = english_name or drug.english_name
                        drug.manufacturer = manufacturer or drug.manufacturer
                        drug.applicant = applicant or drug.applicant
                        drug.dosage_form = dosage_form or drug.dosage_form
                        drug.packaging = packaging or drug.packaging
                        drug.indications = indications or drug.indications
                        drug.active_ingredients = ingredients or drug.active_ingredients
                        drug.target_animals = target_animals or drug.target_animals
                        drug.save()
                        updated_count += 1
                        self.stdout.write(f"[U] 更新: {chinese_name}")
                    else:
                        self.stdout.write(f"[-] 跳過: {chinese_name} (已存在)")
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"處理第 {index+1} 筆資料時發生錯誤: {e}")
                    self.stdout.write(f"[X] 處理第 {index+1} 筆資料時發生錯誤: {e}")
                    continue
            
            # 輸出結果統計
            self.stdout.write(self.style.SUCCESS("同步完成！"))
            self.stdout.write(f"  新增: {created_count} 筆")
            self.stdout.write(f"  更新: {updated_count} 筆") 
            self.stdout.write(f"  錯誤: {error_count} 筆")
            self.stdout.write(f"  總計處理: {len(data)} 筆")
            
            # 更新統計資訊
            total_drugs = AnimalDrug.objects.filter(is_active=True).count()
            self.stdout.write(f"資料庫中目前有 {total_drugs} 筆有效動物用藥資料")
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f"API連接失敗: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"同步過程中發生未預期錯誤: {e}"))
            logger.error(f"sync_animal_drugs command error: {e}")
    
    def _get_field_value(self, item, field_names):
        """
        從item中獲取欄位值，支持多種可能的欄位名稱
        """
        for field_name in field_names:
            if field_name in item and item[field_name]:
                return str(item[field_name]).strip()
        return ""

    def _extract_target_animals(self, indications):
        """
        從效能(適應症)欄位中提取適用動物資訊
        政府資料格式通常是：「豬、牛：治療...」或「犬、貓：用於...」
        """
        if not indications:
            return ""

        import re

        # 常見動物名稱
        animals = ['豬', '牛', '羊', '馬', '犬', '貓', '雞', '鴨', '鵝', '兔', '魚', '蝦']

        # 尋找冒號前的動物名稱模式
        colon_match = re.match(r'^([^：:]+)[：:]', indications)
        if colon_match:
            prefix = colon_match.group(1)
            # 檢查前綴是否包含動物名稱
            found_animals = []
            for animal in animals:
                if animal in prefix:
                    found_animals.append(animal)

            if found_animals:
                return '、'.join(found_animals)

        # 如果沒有找到標準格式，搜索整個文本中的動物名稱
        found_animals = []
        for animal in animals:
            if animal in indications:
                found_animals.append(animal)

        return '、'.join(found_animals) if found_animals else ""