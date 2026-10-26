# خطوات التنفيذ الكاملة: RMX3241 / F.12 / LATAM

[English](guide.en.md) · [تشخيص الأعطال](troubleshooting.md) · [الأجهزة الأخرى](other-devices.md)

اقرأ التسلسل كاملًا قبل التنفيذ. فتح البوتلودر **مسح بيانات الهاتف في التجربة الأصلية**.
انسخ الصور والملفات الشخصية بشكل مستقل. نسخة الأقسام هنا تستثني userdata وsuper وcache،
ولا تمثل نسخة كاملة تضمن استرجاع كل النظام أو بيانات المستخدم. تعديل preloader قد يمنع
الإقلاع؛ احفظ نسخة هاتفك الأصلية وتوقف إذا فشل أي تحقق.

## 0. ما الذي جرى اختباره؟

الهاتف: RMX3241 / RE513CL1، Android 13، البناء RMX3241_11_F.12، منطقة LATAM،
معالج MT6833 وتخزين UFS. سُجل project 20796 وNV ID 10011010 في الحالة الأصلية.
أوامر الكتابة ترفض هوية أخرى. التشابه بالاسم أو المعالج وحده لا يثبت التوافق.

بيئة التجربة: Ubuntu 26.04.1 x86_64، Python 3.14.4، Platform-Tools 36.0.0،
Antumbra 2.0.0، Magisk 30.7. الريبو يحتاج Python 3.11 أو أحدث. السكربتات الجديدة
منظمة حول نفس المسار، لكنها لم تُعد دورة الكتابة كاملة على جهاز آخر؛ فحوصها الآلية
لا تُقدّم كبديل عن اختبار عتاد جديد.

تهيئة جهاز Ubuntu 26.04:

```bash
sudo apt install git usbutils python3 python3-venv python3-pip \
  libusb-1.0-0 libudev1 libfuse2t64
python3 -m venv --without-pip .venv
python3 -m pip --python .venv/bin/python3 install -r requirements.txt
.venv/bin/python3 -m rootguide fetch-tools
```

قد يكون اسم FUSE2 في توزيعة أقدم libfuse2. ملفات التشغيل المنزلة تخص Linux x86_64؛
لم نختبر هذا المسار على Windows أو macOS. التنزيلات والمصادر داخل local/tools،
مع فحص SHA256 ولقطات Git المثبتة. راجع [مصادر وتراخيص الأدوات](../THIRD_PARTY.md).
فشل بصمة ملف أو مصدر DA سبب للتوقف، وليس لتجريب ملف عشوائي.

## 1. التعاريف والاتصال

```bash
sudo install -m 0644 drivers/70-realme-mtk.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
id -nG
```

المستخدم الأصلي عضو في plugdev؛ إضافة العضوية حديثًا تحتاج تسجيل خروج ودخول.
تحتاج بعض التوزيعات أيضًا قواعد Android الخاصة بـADB وfastboot. هذه قاعدة خدمة
Linux، وليست ملف تعريف VCOM لـWindows.

فعّل خيارات المطوّر بالضغط على رقم الإصدار 7 مرات، ثم OEM unlocking وUSB debugging.
وصل هاتفًا واحدًا فقط، وافتح الشاشة، ووافق على بصمة الكمبيوتر. استعمل كيبل بيانات
ومنفذ USB مباشرًا. معرّفات USB المشاهدة:

| الوضع | VID:PID |
|---|---|
| Android / ADB | 22d9:2769 أو 22d9:2765 |
| OPLUS Preloader أو DA المحمّل | 22d9:0006 |
| Fastboot | 0e8d:201c |
| BROM الذي لم نصل إليه خلال التجربة | 0e8d:0003 |

```bash
.venv/bin/python3 -m rootguide doctor
```

يلزم ظهور supported_profile بقيمة rmx3241-f12. عند ظهور unsupported توقف.
الرقم التسلسلي لا يطبع صريحًا، بل كبصمة. الأوامر الداعمة تقبل --serial لتحديد هاتف
ADB، لكن قبل أي عملية DA افصل جميع الهواتف الأخرى لأن أداة DA تختار منفذ الخدمة.

## 2. النسخة الاحتياطية

```bash
.venv/bin/python3 -m rootguide backup
.venv/bin/python3 -m rootguide backup --execute
```

الأول يعرض الخطة فقط. الثاني يسجل هوية الهاتف محليًا، ويشغّل مستمع Antumbra عبر
libusb، ثم يرسل adb reboot edl للهاتف المحدد. رغم اسم الأمر، الوضع الفعلي الذي ظهر
كان OPLUS Preloader الخاص بـMediaTek. تُحمّل مرحلتا DA مع Carbonara والامتدادات.

تُحفظ الملفات في local/session/backups. تُفحص أحجامها وبصماتها وCRC لرأس GPT
ومصفوفة الأقسام. لا تُكتب جلسة فوق جلسة موجودة. لاستخدام مسار آخر أضف
`--session local/اسم-الجلسة` بصورة متسقة لكل الأوامر اللاحقة.

جدول هذا الهاتف يعلن FirstUsableLBA=34، مع أن recovery يبدأ بالقطاع 8 وينتهي
32775 بحجم قطاع 4096. تحقق هذا المسار يسمح بهذه الحالة المعروفة تحديدًا؛ تبقى
بصمات CRC وحدود بيانات GPT وعدم تداخل الأقسام شروطًا إلزامية.

```bash
.venv/bin/python3 -m rootguide verify-backups
.venv/bin/python3 -m rootguide shutdown-da
```

تبقى DA محمّلة بعد خروج أمر Antumbra؛ لا تبدأ مصافحة BROM جديدة بأداة أخرى على
هذا الاتصال نفسه. shutdown-da يتصل بالـDA الموجودة مباشرة. قد يبقى الهاتف مطفأً
بعد الإقرار بالأمر؛ اضغط التشغيل 3 ثوانٍ، ودعه يقلع، ثم أعد اتصال ADB.

في الحالة الأصلية حُفظ 54 قسمًا بإجمالي 1,358,987,264 بايت. هذا عدد الحالة المسجلة،
وليس شرطًا لكل جدول أقسام. تشمل الملفات boot وpreloader الأساسي والثانوي وseccfg
وrecovery والمعايرة. لا تشمل الصور والملفات الشخصية أو userdata أو super أو cache.
لا تنشر النسخ أو ملفات المعايرة في الريبو أو Issues.

## 3. تعديل boot على الهاتف نفسه

```bash
.venv/bin/python3 -m rootguide patch-boot
.venv/bin/python3 -m rootguide patch-boot --execute
```

الأول خطة. الثاني يثبت APK الرسمي ذي البصمة المتحققة، ويستخرج أدوات ARM64 منه،
وينقل boot الأصلي من هذه الجلسة إلى الهاتف نفسه، ويشغّل boot_patch.sh الأصلي.
لا يفلش أي قسم. الناتج local/session/images/boot-patched.img ومعه سجل يربطه
ببصمة boot الأصلي وAPK والجلسة.

المفاتيح المستخدمة: BOOTMODE=true، KEEPVERITY=true، KEEPFORCEENCRYPT=true،
PATCHVBMETAFLAG=false، RECOVERYMODE=false، LEGACYSAR=false. اختير cache لتخزين
pre-init في التجربة الأصلية. اسم الإدخال boot.img؛ تجنب stock_boot.img لأنه اسم
مؤقت يستخدمه سكربت Magisk داخليًا. صورة boot الأصلية 32 MiB وبداخلها ramdisk.

## 4. تعديل الوصول إلى fastboot في preloader

هذه مرحلة إقلاع مبكرة. استخدم نسخة هذا الهاتف الأصلية فقط.

```bash
.venv/bin/python3 -m rootguide patch-preloader
.venv/bin/python3 -m rootguide plan --partition preloader \
  --image local/session/images/preloader-patched.bin
.venv/bin/python3 -m rootguide flash --partition preloader
```

الأداة تتحقق من نسخة مصدر المعدّل، وحجم 4 MiB، وتنسيق COMBO_BOOT، والمساحة الفارغة،
وبقاء الكود الموقّع حرفيًا بعد نقله، وعلم ROMINFO المتوقع. راجع الخطة والبصمات.
الأمر الأخير أعلاه عرض فقط. للكتابة المقصودة على النسخة الأساسية:

```bash
.venv/bin/python3 -m rootguide flash --partition preloader \
  --execute --confirm RMX3241
```

تُفحص هوية الهاتف ونسخه وبصمات الخطة والأدوات قبل إعادة التشغيل. تُكتب النسخة الأساسية
فقط، ثم تُقرأ 4 MiB كاملة وتُقارن بالملف. لا تُكتب النسخة الثانوية. يُقرأ GPT حديث
ويُتحقق من مطابقته للنسخة. لا يرسل shutdown تلقائيًا إلا بعد نجاح التحقق.
بعدها شغّل الهاتف وأعد ADB.

سبق هذه الخطوة في التجربة الأصلية أمر seccfg unlock لم يثبت فتح Android فعليًا.
الريبو يوثّقه كمرحلة فاشلة ولا يعيده خفيةً. لم تُجر تجربة عتاد منفصلة تثبت إن كان
لهذه الكتابة السابقة أثر على السلوك اللاحق؛ لذلك لا ندّعي أن السكربتات الجديدة
أُثبتت على هاتف جديد من البداية للنهاية.

## 5. فتح البوتلودر القياسي ومسح البيانات

تأكد من نسخ ملفاتك الشخصية وتفعيل OEM unlocking، ثم استخدم الأدوات المنزلة مع هاتف واحد:

```bash
local/tools/platform-tools/adb reboot bootloader
local/tools/platform-tools/fastboot devices
local/tools/platform-tools/fastboot getvar product
local/tools/platform-tools/fastboot getvar unlocked
local/tools/platform-tools/fastboot flashing get_unlock_ability
```

قبل الفتح ظهر unlocked: no وsecure: yes. عندما تكون مستعدًا لمسح البيانات نفّذ يدويًا:

```bash
local/tools/platform-tools/fastboot flashing unlock
```

اقرأ شاشة الهاتف ووافق بزر الصوت المحدد فيها. لا تفترض نفس الزر لكل إصدار.
انتظر الإكمال، ثم افحص:

```bash
local/tools/platform-tools/fastboot getvar product
local/tools/platform-tools/fastboot getvar unlocked
local/tools/platform-tools/fastboot getvar secure
```

النتيجة المسجلة: k6833v1_64_k419، unlocked: yes، secure: no.
إذا ظهرت ردود متناقضة أو متأخرة، توقف وراجع التشخيص. لا تكفي استجابة واحدة مبهمة.

أقلع إلى النظام واترك المسح والإعداد يكتملان. أكمل Hello Setup، وفعّل USB debugging
وسماح الكمبيوتر مرة ثانية. في الحالة الأصلية احتاج fastboot غير المستجيب وهو خامل
فصل USB وضغط التشغيل ورفع الصوت نحو 30 ثانية؛ لا تستخدم هذا لإيقاف كتابة جارية.

```bash
.venv/bin/python3 -m rootguide doctor
```

يجب إثبات flash.locked=0 وdevice_state=unlocked من Android بعد الإقلاع، لا الاكتفاء
برسالة نجاح أداة. ظهرت verifiedbootstate=orange في الحالة الأصلية.

## 6. كتابة boot المعدل عبر MediaTek

```bash
.venv/bin/python3 -m rootguide plan --partition boot \
  --image local/session/images/boot-patched.img
.venv/bin/python3 -m rootguide flash --partition boot
.venv/bin/python3 -m rootguide flash --partition boot \
  --execute --confirm RMX3241
```

الكتابة تتطلب هاتف الجلسة نفسه وبناءه، ونسخه السليمة، ومصدر تعديل boot نفسه، وأدوات
وملفًا مطابقين للخطة، وإثبات فتح البوتلودر من Android. يُكتب القسم باسمه بواسطة
Antumbra؛ ثم يشتق قارئ التحقق العنوان من GPT حديث وصحيح بدل افتراض عنوان عالمي.
فشل القراءة أو اختلاف البصمة يوقف إعادة التشغيل التلقائية ويطلب مراجعة السجل.

كان عنوان boot في الحالة الأصلية 0x47D00000 وطوله 0x2000000. هذه أرقام توثيق،
ولا تنقل لجهاز آخر. محاولة fastboot flash boot توقفت عند Sending قبل Writing،
أما الكتابة التي نجحت فكانت عبر DA.

## 7. التطبيق وإثبات الروت

بعد التحقق وshutdown شغّل الهاتف إذا بقي مطفأً، وانتظر دخول Android. لأن الفتح مسح
التطبيقات، ثبت Magisk مجددًا:

```bash
local/tools/platform-tools/adb install -r local/tools/Magisk-v30.7.apk
local/tools/platform-tools/adb shell am start -n com.topjohnwu.magisk/.ui.MainActivity
```

وافق في التطبيق على Requires additional setup ثم OK، واترك إعادة التشغيل تكتمل.
بعدها يظهر Installed 30.7 (30700). وافق على طلب Shell أو فعّله من صفحة Superuser
لفحص الروت الصريح:

```bash
.venv/bin/python3 -m rootguide verify-root
```

النجاح هو ظهور uid=0(root). في التجربة ظهرت أيضًا groups=0(root)
وcontext=u:r:magisk:s0، وإصدار Magisk 30.7:MAGISK:R ورقمه 30700.
تثبيت APK أو فتح البوتلودر وحده لا يثبت الروت.

لم نحتج تعديل vbmeta أو super أو recovery أو تركيب TWRP أو نواة أو وحدات إضافية.
لم نفحص مستقلًا كل التطبيقات أو Play Integrity أو كل وظائف الشبكة أو استرجاعًا كاملًا.
احتفظ بالأصول، ولا تعاود قفل البوتلودر مع boot المعدل. قبل OTA جديد راجع توافق البناء
واستخرج الصورة المناسبة له. المصادر واللقطات والبصمات مثبتة في assets.lock.json،
وروابطها موضحة في [النسخة الإنجليزية](guide.en.md#references).
