# AI Router Studio — V1

نمونه اولیهٔ یک AI Project Orchestrator با رویکرد صفر-هزینه.

## امکانات V1
- Prompt Compiler قانون‌محور
- Task Decomposer
- Difficulty Analyzer
- Token estimator
- Zero-budget guard
- Preview-before-build
- Approval Gate
- شبیه‌ساز اجرای Taskها
- رابط فارسی RTL و responsive

## قوانین هسته
1. عملیات ساخت مهم قبل از تأیید کاربر اجرا نمی‌شود.
2. MVP هیچ Provider پولی را خودکار صدا نمی‌زند.
3. محدودسازی Context و صرفه‌جویی Token بخشی از Plan است.
4. معماری مستقل از Provider است.

## مسیر نسخه‌های بعد
- Provider Adapter واقعی
- مدل محلی
- APIهای رایگانِ مجاز و دارای سهمیه
- Web Research
- Image generation
- Project memory
- Semantic cache
- Executor واقعی برای کد و وب
- GitHub PR و commit
- اتصال اختیاری به LiteLLM یا Dify

## اجرا
فایل ai-router/index.html را مستقیم در مرورگر باز کن. برای MVP نصب npm لازم نیست.