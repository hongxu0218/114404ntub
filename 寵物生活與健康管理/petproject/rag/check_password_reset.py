#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import sys

def check_password_reset_content():
    print("=== 檢查知識庫中的忘記密碼相關內容 ===\n")

    try:
        # 讀取平台手冊
        df_manual = pd.read_excel('data/platform_manual.xlsx')
        print("Platform Manual 內容:")
        print(df_manual.to_string())
        print("\n" + "="*50 + "\n")

        # 檢查是否有忘記密碼相關問題
        print("尋找忘記密碼相關問題:")
        found_password_reset = False

        for i, row in df_manual.iterrows():
            q = str(row.get('Question', ''))
            a = str(row.get('Answer', ''))

            # 檢查問題中是否包含密碼相關關鍵字
            keywords = ['忘記密碼', '重設密碼', '密碼', 'password', 'reset', '找回密碼', '重新設定', '更改密碼']
            for keyword in keywords:
                if keyword in q or keyword in a:
                    print(f"找到相關內容:")
                    print(f"問題: {q}")
                    print(f"答案: {a}")
                    print("-" * 30)
                    found_password_reset = True
                    break

        if not found_password_reset:
            print("❌ 知識庫中沒有找到忘記密碼相關的內容")
            print("\n建議添加以下FAQ:")
            print("Q: 忘記密碼怎麼辦？")
            print("A: 1. 點擊登入頁面的「忘記密碼？」連結")
            print("   2. 輸入您註冊時使用的電子郵件地址")
            print("   3. 點擊「發送重設密碼郵件」")
            print("   4. 檢查您的電子郵件信箱（包含垃圾郵件資料夾）")
            print("   5. 點擊郵件中的重設密碼連結")
            print("   6. 設定新的密碼並確認")
            print("   7. 使用新密碼登入系統")
            print("\n   如果沒有收到郵件，請：")
            print("   - 確認電子郵件地址輸入正確")
            print("   - 檢查垃圾郵件資料夾")
            print("   - 等待幾分鐘後再次嘗試")
            print("   - 或聯繫客服協助處理")
        else:
            print("✅ 找到忘記密碼相關內容")

    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}")

if __name__ == "__main__":
    check_password_reset_content()