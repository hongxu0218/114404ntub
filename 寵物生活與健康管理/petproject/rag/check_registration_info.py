#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import sys

def check_registration_content():
    print("=== 檢查知識庫中的註冊相關內容 ===\n")

    try:
        # 讀取平台手冊
        df_manual = pd.read_excel('data/platform_manual.xlsx')
        print("Platform Manual 內容:")
        print(df_manual.to_string())
        print("\n" + "="*50 + "\n")

        # 檢查是否有註冊相關問題
        print("尋找註冊相關問題:")
        found_registration = False

        for i, row in df_manual.iterrows():
            q = str(row.get('Question', ''))
            a = str(row.get('Answer', ''))

            # 檢查問題中是否包含註冊相關關鍵字
            keywords = ['註冊', '帳號', '登入', '申請', 'register', 'signup', 'login']
            for keyword in keywords:
                if keyword in q or keyword in a:
                    print(f"找到相關內容:")
                    print(f"問題: {q}")
                    print(f"答案: {a}")
                    print("-" * 30)
                    found_registration = True
                    break

        if not found_registration:
            print("❌ 知識庫中沒有找到註冊相關的內容")
            print("\n建議添加以下FAQ:")
            print("Q: 如何註冊毛日好帳號？")
            print("A: 1. 點擊右上角「登入/註冊」按鈕")
            print("   2. 選擇「註冊新帳號」")
            print("   3. 填寫用戶名、電子郵件和密碼")
            print("   4. 點擊「註冊」完成帳號創建")
            print("   5. 或者可以選擇使用Google帳號快速註冊")
        else:
            print("✅ 找到註冊相關內容")

    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}")

if __name__ == "__main__":
    check_registration_content()