#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json

def test_password_reset_query():
    url = "http://127.0.0.1:8001/ask"

    # 測試忘記密碼相關問題
    queries = [
        "忘記密碼怎麼辦？",
        "怎麼重設密碼",
        "password reset",
        "密碼忘了",
        "找回密碼"
    ]

    for query in queries:
        print(f"\n測試問題: {query}")

        data = {
            "q": query,
            "top_k": 3
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            print(f"狀態碼: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"回應: {result.get('answer', 'No answer field')}")
                print(f"相關度分數: {result.get('score', 'No score')}")
            else:
                print(f"錯誤: {response.text}")

        except Exception as e:
            print(f"請求失敗: {e}")

if __name__ == "__main__":
    test_password_reset_query()